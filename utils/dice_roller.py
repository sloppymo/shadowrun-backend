"""
Safe dice rolling utility for Shadowrun RPG
No eval() usage - all parsing is done safely
"""
import re
import random
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
from utils.validators import DiceNotationSchema
from pydantic import ValidationError


@dataclass
class DiceRoll:
    """Represents a single dice roll result"""
    num_dice: int
    dice_size: int
    modifier: int
    rolls: List[int]
    total: int
    notation: str


class DiceRoller:
    """Safe dice rolling implementation"""
    
    # Shadowrun-specific dice mechanics
    SHADOWRUN_D6 = 6
    SHADOWRUN_SUCCESS_THRESHOLD = 5
    SHADOWRUN_GLITCH_THRESHOLD = 0.5  # More than half the dice show 1s
    
    def __init__(self):
        self.random = random.Random()
    
    def parse_notation(self, notation: str) -> Tuple[int, int, int]:
        """
        Safely parse dice notation like '3d6', '2d10+5', '4d8-2'
        Returns: (num_dice, dice_size, modifier)
        """
        # Validate notation first
        try:
            validator = DiceNotationSchema(notation=notation)
            notation = validator.notation
        except ValidationError as e:
            raise ValueError(f"Invalid dice notation: {e}")
        
        # Parse with regex
        pattern = r'^(\d+)d(\d+)([+\-]\d+)?$'
        match = re.match(pattern, notation.lower())
        
        if not match:
            raise ValueError(f"Invalid dice notation: {notation}")
        
        num_dice = int(match.group(1))
        dice_size = int(match.group(2))
        
        # Parse modifier if present
        modifier = 0
        if match.group(3):
            modifier = int(match.group(3))
        
        return num_dice, dice_size, modifier
    
    def roll(self, notation: str) -> DiceRoll:
        """
        Roll dice based on notation
        
        Args:
            notation: Dice notation string (e.g., '3d6', '2d10+5')
            
        Returns:
            DiceRoll object with results
        """
        num_dice, dice_size, modifier = self.parse_notation(notation)
        
        # Roll the dice
        rolls = [self.random.randint(1, dice_size) for _ in range(num_dice)]
        total = sum(rolls) + modifier
        
        return DiceRoll(
            num_dice=num_dice,
            dice_size=dice_size,
            modifier=modifier,
            rolls=rolls,
            total=total,
            notation=notation
        )
    
    def roll_shadowrun(self, dice_pool: int, edge_used: bool = False) -> Dict:
        """
        Roll Shadowrun 6e dice pool
        
        Args:
            dice_pool: Number of d6 to roll
            edge_used: Whether Edge is being used (exploding 6s)
            
        Returns:
            Dict with hits, glitch status, and individual rolls
        """
        if dice_pool < 1:
            raise ValueError("Dice pool must be at least 1")
        if dice_pool > 50:
            raise ValueError("Dice pool cannot exceed 50")
        
        rolls = []
        hits = 0
        ones = 0
        
        # Initial roll
        for _ in range(dice_pool):
            roll = self.random.randint(1, self.SHADOWRUN_D6)
            rolls.append(roll)
            
            if roll >= self.SHADOWRUN_SUCCESS_THRESHOLD:
                hits += 1
            if roll == 1:
                ones += 1
        
        # Handle Edge (exploding 6s)
        if edge_used:
            sixes = [r for r in rolls if r == 6]
            extra_rolls = []
            
            while sixes:
                new_sixes = []
                for _ in sixes:
                    roll = self.random.randint(1, self.SHADOWRUN_D6)
                    extra_rolls.append(roll)
                    
                    if roll >= self.SHADOWRUN_SUCCESS_THRESHOLD:
                        hits += 1
                    if roll == 6:
                        new_sixes.append(roll)
                
                sixes = new_sixes
            
            rolls.extend(extra_rolls)
        
        # Check for glitch
        glitch = ones > len(rolls) * self.SHADOWRUN_GLITCH_THRESHOLD
        critical_glitch = glitch and hits == 0
        
        return {
            'dice_pool': dice_pool,
            'rolls': rolls,
            'hits': hits,
            'ones': ones,
            'glitch': glitch,
            'critical_glitch': critical_glitch,
            'edge_used': edge_used
        }
    
    def roll_initiative(self, reaction: int, intuition: int, 
                       initiative_dice: int = 1, edge_used: bool = False) -> Dict:
        """
        Roll Shadowrun initiative
        
        Args:
            reaction: Character's Reaction attribute
            intuition: Character's Intuition attribute  
            initiative_dice: Number of initiative dice (usually 1, but can be more)
            edge_used: Whether Edge is being used
            
        Returns:
            Dict with initiative score and breakdown
        """
        base = reaction + intuition
        
        # Roll initiative dice
        dice_rolls = []
        for _ in range(initiative_dice):
            roll = self.random.randint(1, self.SHADOWRUN_D6)
            dice_rolls.append(roll)
        
        # Edge adds exploding 6s to initiative
        if edge_used:
            extra_rolls = []
            sixes = [r for r in dice_rolls if r == 6]
            
            while sixes:
                new_sixes = []
                for _ in sixes:
                    roll = self.random.randint(1, self.SHADOWRUN_D6)
                    extra_rolls.append(roll)
                    if roll == 6:
                        new_sixes.append(roll)
                sixes = new_sixes
            
            dice_rolls.extend(extra_rolls)
        
        total = base + sum(dice_rolls)
        
        return {
            'base': base,
            'dice_rolls': dice_rolls,
            'total': total,
            'edge_used': edge_used
        }
    
    def roll_extended_test(self, dice_pool: int, threshold: int, 
                          interval: str = "1 minute", max_rolls: Optional[int] = None) -> Dict:
        """
        Roll an extended test
        
        Args:
            dice_pool: Number of dice to roll each interval
            threshold: Total hits needed
            interval: Time per roll (for narrative purposes)
            max_rolls: Maximum number of rolls allowed (None for unlimited)
            
        Returns:
            Dict with test results
        """
        rolls_made = 0
        total_hits = 0
        roll_history = []
        glitched = False
        
        while total_hits < threshold:
            rolls_made += 1
            
            # Check max rolls
            if max_rolls and rolls_made > max_rolls:
                break
            
            # Reduce dice pool by 1 per roll (fatigue)
            current_pool = max(1, dice_pool - (rolls_made - 1))
            
            # Roll the dice
            result = self.roll_shadowrun(current_pool)
            roll_history.append(result)
            
            total_hits += result['hits']
            if result['glitch']:
                glitched = True
            
            # Critical glitch ends the test
            if result['critical_glitch']:
                break
        
        success = total_hits >= threshold
        time_taken = f"{rolls_made} x {interval}"
        
        return {
            'success': success,
            'threshold': threshold,
            'total_hits': total_hits,
            'rolls_made': rolls_made,
            'time_taken': time_taken,
            'roll_history': roll_history,
            'glitched': glitched
        }
    
    def format_roll_result(self, result: DiceRoll) -> str:
        """Format a dice roll result for display"""
        rolls_str = ', '.join(map(str, result.rolls))
        
        if result.modifier > 0:
            return f"Rolled {result.notation}: [{rolls_str}] + {result.modifier} = **{result.total}**"
        elif result.modifier < 0:
            return f"Rolled {result.notation}: [{rolls_str}] - {abs(result.modifier)} = **{result.total}**"
        else:
            return f"Rolled {result.notation}: [{rolls_str}] = **{result.total}**"
    
    def format_shadowrun_result(self, result: Dict) -> str:
        """Format a Shadowrun dice pool result for display"""
        rolls_str = ', '.join(map(str, result['rolls']))
        
        output = f"Rolled {result['dice_pool']}d6: [{rolls_str}]\n"
        output += f"**Hits:** {result['hits']}"
        
        if result['edge_used']:
            output += " (Edge used - 6s exploded)"
        
        if result['critical_glitch']:
            output += "\n🔥 **CRITICAL GLITCH!** 🔥"
        elif result['glitch']:
            output += "\n⚠️ **GLITCH!** ⚠️"
        
        return output


# Global dice roller instance
dice_roller = DiceRoller()


# Convenience functions
def roll(notation: str) -> DiceRoll:
    """Roll dice using standard notation"""
    return dice_roller.roll(notation)


def roll_shadowrun(dice_pool: int, edge_used: bool = False) -> Dict:
    """Roll Shadowrun dice pool"""
    return dice_roller.roll_shadowrun(dice_pool, edge_used)


def roll_initiative(reaction: int, intuition: int, 
                   initiative_dice: int = 1, edge_used: bool = False) -> Dict:
    """Roll Shadowrun initiative"""
    return dice_roller.roll_initiative(reaction, intuition, initiative_dice, edge_used) 
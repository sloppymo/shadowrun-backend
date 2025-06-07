# Testing and Quality Assurance Guide

## Overview

This document outlines comprehensive testing strategies for the Shadowrun RPG system's new features, focusing on integration with existing functionality, performance benchmarks, and user acceptance testing.

## 1. Unit Testing

### Combat System Tests

```python
def test_initiative_calculation():
    # Test that initiative is correctly calculated
    character = Character(
        attributes=json.dumps({
            "reaction": 4,
            "intuition": 3,
            "initiative_dice": 2
        })
    )
    
    # Mock dice rolls to return predictable values
    with patch('random.randint', return_value=4):
        initiative = calculate_initiative(character)
        # Should be reaction + intuition + (dice × fixed roll)
        assert initiative == 4 + 3 + (2 × 4) == 15
```

### NPC Generation Tests

```python
def test_npc_generation_by_template():
    template = NPCTemplate.query.filter_by(name="Corporate Security").first()
    
    # Test with fixed random seed for deterministic results
    with patch('random.seed', return_value=None):
        with patch('random.choice', side_effect=lambda x: x[0]):
            npc = generate_npc(template.id, "lieutenant")
            
            # Check basic structure
            assert "name" in npc
            assert "attributes" in npc
            assert "skills" in npc
            
            # Check attribute distribution matches template priorities
            attr_priorities = json.loads(template.attribute_priorities)
            # First priority should have highest value
            assert npc["attributes"][attr_priorities[0]] >= 4
```

### AI Response Tests

```python
@pytest.mark.asyncio
async def test_gm_context_building():
    # Create test session with characters and scene
    session_id = create_test_session()
    
    # Build context for LLM
    context = build_gm_context(session_id)
    
    # Verify context contains all required elements
    assert "Current scene:" in context[0]["content"]
    assert "The requesting character" in context[0]["content"]
    assert "Game state:" in context[0]["content"]
```

## 2. Integration Testing

### Combat-NPC Integration

```python
def test_npc_in_combat():
    # Create test session
    session_id = create_test_session()
    
    # Generate NPC
    npc_id = generate_and_save_npc(session_id, "corporate", "lieutenant")
    
    # Start combat
    combat_id = start_combat(session_id)
    
    # Add NPC to combat
    add_entity_to_combat(combat_id, npc_id)
    
    # Verify NPC appears in initiative order
    initiative_order = get_initiative_order(combat_id)
    assert any(entity["id"] == npc_id for entity in initiative_order)
    
    # Test NPC attack action
    attack_result = npc_attack(npc_id, player_character_id)
    assert "damage" in attack_result
```

### DM Review System Integration

```javascript
describe('DM Review System Integration', () => {
  test('AI Response enters review queue', async () => {
    // Mock player action
    const playerAction = {
      sessionId: 'test-session',
      characterId: 'test-character',
      action: 'I ask the Johnson about payment details'
    };
    
    // Submit action through API
    const response = await axios.post('/api/player/action', playerAction);
    
    // Check that the response is pending review
    expect(response.data.status).toBe('pending_review');
    
    // Check that it appears in the DM review queue
    const reviewQueue = await axios.get('/api/dm/review-queue');
    const pendingItem = reviewQueue.data.items.find(
      item => item.action === playerAction.action
    );
    expect(pendingItem).toBeDefined();
  });
  
  test('DM approved response is delivered to player', async () => {
    // Setup mock pending review
    const reviewId = await setupMockPendingReview();
    
    // Approve the review
    await axios.post(`/api/dm/review/${reviewId}/approve`);
    
    // Check that the player received the response
    const playerMessages = await axios.get('/api/player/messages');
    const approvedMessage = playerMessages.data.messages.find(
      msg => msg.reviewId === reviewId
    );
    expect(approvedMessage).toBeDefined();
    expect(approvedMessage.status).toBe('delivered');
  });
});
```

## 3. Performance Testing

### Response Time Benchmarks

```python
@pytest.mark.benchmark
def test_npc_generation_performance(benchmark):
    # Measure NPC generation time
    result = benchmark(
        generate_npc,
        template_id=1,
        power_level="lieutenant"
    )
    
    # Should generate within 100ms
    assert benchmark.stats.stats.mean < 0.1

@pytest.mark.benchmark
def test_combat_resolution_performance(benchmark):
    # Setup test combat scenario
    session_id = create_test_combat_scenario()
    
    # Measure combat turn resolution time
    result = benchmark(
        resolve_combat_turn,
        session_id=session_id
    )
    
    # Combat turn should resolve within 200ms
    assert benchmark.stats.stats.mean < 0.2
```

### LLM Response Time Testing

```python
@pytest.mark.asyncio
@pytest.mark.benchmark
async def test_llm_response_time(benchmark):
    # Prepare test prompt
    messages = [
        {"role": "system", "content": "You are a Shadowrun GM."},
        {"role": "user", "content": "What happens when I enter the corporate building?"}
    ]
    
    # Measure LLM response time
    result = await benchmark(
        call_llm,
        model="openai",
        messages=messages,
        stream=False
    )
    
    # Response should complete within 2 seconds
    assert benchmark.stats.stats.mean < 2.0
```

### Image Generation Performance

```python
@pytest.mark.benchmark
def test_image_generation_performance(benchmark):
    # Prepare scene description
    scene = "A neon-lit street corner with rain falling on augmented citizens"
    
    # Measure image generation time
    result = benchmark(
        generate_scene_image,
        description=scene,
        style="cyberpunk"
    )
    
    # Should generate within 3 seconds
    assert benchmark.stats.stats.mean < 3.0
```

## 4. Load Testing

```python
def test_concurrent_user_load():
    # Setup test environment
    base_url = "http://localhost:5000"
    
    # Define user actions
    def user_workflow():
        # Login
        session = requests.Session()
        resp = session.post(f"{base_url}/api/login", json={
            "username": f"test_user_{random.randint(1, 1000)}",
            "password": "password"
        })
        assert resp.status_code == 200
        
        # Create or join session
        resp = session.post(f"{base_url}/api/create_session")
        session_id = resp.json()["session_id"]
        
        # Send commands
        for _ in range(10):
            resp = session.post(f"{base_url}/api/command", json={
                "session_id": session_id,
                "command": f"I look around the {random.choice(['street', 'bar', 'building'])}"
            })
            assert resp.status_code == 200
            time.sleep(1)
    
    # Run with concurrent users
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(user_workflow) for _ in range(10)]
        for future in concurrent.futures.as_completed(futures):
            assert not future.exception()
```

## 5. User Acceptance Testing

### Test Scenarios

#### Combat Scenario
```
1. GM initiates combat with corporate security
2. System generates 4 security guards using templates
3. Initiative is rolled automatically
4. Each player takes their turn using combat commands
5. AI GM describes outcomes and environmental effects
6. GM can override or modify any result through review interface
```

#### NPC Interaction Scenario
```
1. Players enter a bar in the Redmond Barrens
2. System generates bartender and patrons based on location
3. Players interact with NPCs via natural language
4. AI GM provides responses based on NPC personality and motivations
5. GM reviews key responses before delivery to players
6. Test that NPCs remember previous interactions
```

#### Matrix Hacking Scenario
```
1. Decker character initiates Matrix connection
2. System generates host based on corporation type
3. Decker performs series of hacking actions
4. AI GM describes IC responses and security systems
5. Test that host security level escalates appropriately
6. Verify matrix damage affects meat space character
```

### User Experience Questionnaire

After each testing session, participants complete a questionnaire covering:

1. **Overall Satisfaction** (1-10 scale)
2. **System Responsiveness** (1-10 scale)
3. **AI GM Quality** (1-10 scale with comments)
4. **Feature Usefulness** (Rate each new feature)
5. **Interface Usability** (1-10 scale with comments)
6. **Narrative Cohesion** (How well did the story flow?)
7. **Technical Issues** (Report any bugs or problems)
8. **Improvement Suggestions** (Open-ended)

## 6. Automated Testing Pipeline

```yaml
# .github/workflows/test.yml
name: Shadowrun System Tests

on:
  push:
    branches: [ main, dev ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-cov pytest-benchmark
    
    - name: Run unit tests
      run: |
        pytest tests/unit/ --cov=app
    
    - name: Run integration tests
      run: |
        pytest tests/integration/
    
    - name: Run performance tests
      run: |
        pytest tests/performance/ --benchmark-only
    
    - name: Upload test results
      uses: actions/upload-artifact@v3
      with:
        name: test-results
        path: |
          .coverage
          benchmark.json
```

## 7. Bug Reporting and Tracking

### Bug Template

```markdown
## Bug Report

### Description
[Concise description of the issue]

### Environment
- Backend Version: [version]
- Frontend Version: [version]
- Browser: [browser and version]
- OS: [operating system]

### Steps to Reproduce
1. [First step]
2. [Second step]
3. [And so on...]

### Expected Behavior
[What should happen]

### Actual Behavior
[What actually happens]

### Screenshots/Logs
[Attach relevant screenshots or log output]

### Severity
- [ ] Critical (System crash, data loss)
- [ ] Major (Feature completely broken)
- [ ] Minor (Feature works but has issues)
- [ ] Cosmetic (Visual glitches)

### Additional Context
[Any additional information that might be relevant]
```

## 8. Test Data Generation

```python
def generate_test_data():
    """Generate a complete test dataset for Shadowrun system"""
    
    # Create test users
    users = []
    for i in range(10):
        users.append({
            "id": f"user{i}",
            "name": f"Test Runner {i}",
            "email": f"runner{i}@shadowrun-test.com"
        })
    
    # Create test characters (1-3 per user)
    characters = []
    for user in users:
        for j in range(random.randint(1, 3)):
            characters.append(generate_test_character(user["id"]))
    
    # Create test sessions
    sessions = []
    for i in range(3):
        gm_user = random.choice(users)
        session = {
            "id": f"session{i}",
            "name": f"Test Run {i}",
            "gm_user_id": gm_user["id"],
            "players": [user["id"] for user in random.sample(users, 4) if user["id"] != gm_user["id"]]
        }
        sessions.append(session)
    
    # Generate scene data for each session
    scenes = []
    for session in sessions:
        scenes.append({
            "session_id": session["id"],
            "description": generate_random_scene_description(),
            "entities": generate_random_entities(5)
        })
    
    # Save to test database
    save_test_data(users, characters, sessions, scenes)
```

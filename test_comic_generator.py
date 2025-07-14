"""Test script for the D&D Comic Book Generator."""

import asyncio
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
import json
from datetime import datetime

from comic_generator import ComicBookGenerator
from agents.data_parser import DataParsingAgent
from agents.scene_planner import ScenePlanningAgent  
from agents.visual_description import VisualDescriptionAgent
from agents.image_generator import ImageGenerationCoordinator
from models import Character, Event, Scene, Panel, Mission
from config import settings


class TestDataParsingAgent:
    """Test the data parsing agent with real mission data."""
    
    @pytest.fixture
    def parser(self):
        return DataParsingAgent()
    
    @pytest.fixture
    def mission1_data(self):
        """Load the actual mission 1 data."""
        base_path = Path("data/mission1")
        data = {}
        
        # Read character file
        char_file = base_path / "mission1_chars.txt"
        if char_file.exists():
            data['chars'] = char_file.read_text(encoding='utf-8')
        
        # Read IC logs
        ic_file = base_path / "mission1_ic.txt"
        if ic_file.exists():
            data['ic'] = ic_file.read_text(encoding='utf-8')
        
        # Read OOC logs
        ooc_file = base_path / "mission1_ooc.txt"
        if ooc_file.exists():
            data['ooc'] = ooc_file.read_text(encoding='utf-8')
        
        return data
    
    async def test_parse_characters(self, parser, mission1_data):
        """Test character parsing from real data."""
        if 'chars' not in mission1_data:
            pytest.skip("Character data not available")
        
        characters = await parser.parse_characters(mission1_data['chars'])
        
        assert len(characters) > 0, "Should parse at least one character"
        
        for char in characters:
            assert char.name, f"Character should have a name: {char}"
            assert char.char_class, f"Character should have a class: {char}"
            print(f"Parsed character: {char.name} ({char.char_class})")
    
    async def test_parse_ic_logs(self, parser, mission1_data):
        """Test IC log parsing."""
        if 'ic' not in mission1_data:
            pytest.skip("IC data not available")
        
        events = await parser.parse_ic_logs(mission1_data['ic'])
        
        assert len(events) > 0, "Should parse at least one event"
        
        # Check event structure
        for event in events[:5]:  # Check first 5 events
            assert event.timestamp, f"Event should have timestamp: {event}"
            assert event.character_name, f"Event should have character: {event}"
            assert event.content, f"Event should have content: {event}"
            print(f"Event: {event.character_name} - {event.content[:50]}...")
    
    async def test_parse_ooc_logs(self, parser, mission1_data):
        """Test OOC log parsing for context."""
        if 'ooc' not in mission1_data:
            pytest.skip("OOC data not available")
        
        events = await parser.parse_ooc_logs(mission1_data['ooc'])
        
        # OOC might be empty, that's okay
        print(f"Parsed {len(events)} OOC events")


class TestScenePlanningAgent:
    """Test scene planning with real data."""
    
    @pytest.fixture
    async def sample_events(self):
        """Create sample events for testing."""
        parser = DataParsingAgent()
        
        # Try to use real data if available
        mission1_path = Path("data/mission1/mission1_ic.txt")
        if mission1_path.exists():
            ic_content = mission1_path.read_text(encoding='utf-8')
            events = await parser.parse_ic_logs(ic_content)
            return events[:20]  # Use first 20 events for testing
        
        # Fallback to mock data
        events = [
            Event(
                timestamp=datetime.now(),
                character_name="TestChar",
                content="Test dialogue",
                event_type="dialogue",
                location="Test Location"
            )
        ]
        return events
    
    async def test_group_events_into_scenes(self, sample_events):
        """Test scene grouping logic."""
        planner = ScenePlanningAgent()
        
        scenes = await planner.group_events_into_scenes(sample_events)
        
        assert len(scenes) > 0, "Should create at least one scene"
        
        for scene in scenes:
            assert len(scene.events) > 0, "Scene should have events"
            assert scene.location, "Scene should have a location"
            print(f"Scene: {scene.location} ({len(scene.events)} events)")
    
    async def test_plan_comic_structure(self, sample_events):
        """Test full comic structure planning."""
        planner = ScenePlanningAgent()
        
        scenes = await planner.plan_comic_structure(sample_events)
        
        assert len(scenes) > 0, "Should create scenes"
        
        # Check that panels are assigned
        total_panels = sum(len(scene.panels) for scene in scenes)
        assert total_panels > 0, "Should create panels"
        
        print(f"Created {len(scenes)} scenes with {total_panels} total panels")


class TestVisualDescriptionAgent:
    """Test visual description generation."""
    
    @pytest.fixture
    async def sample_scene(self):
        """Create a sample scene for testing."""
        # Mock a simple scene
        event = Event(
            timestamp=datetime.now(),
            character_name="Eldara",
            content="Eldara draws her sword and advances towards the goblin.",
            event_type="action",
            location="Dark Forest Clearing"
        )
        
        scene = Scene(
            location="Dark Forest Clearing",
            events=[event],
            panels=[Panel(
                events=[event],
                panel_type="action",
                description="Test panel"
            )]
        )
        
        return scene
    
    @patch('agents.visual_description.openai_client.chat.completions.create')
    async def test_generate_panel_description(self, mock_openai, sample_scene):
        """Test panel description generation."""
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "A detailed panel description"
        mock_openai.return_value = mock_response
        
        agent = VisualDescriptionAgent()
        panel = sample_scene.panels[0]
        
        description = await agent.generate_panel_description(panel, sample_scene)
        
        assert description, "Should generate a description"
        print(f"Generated description: {description}")
    
    @patch('agents.visual_description.openai_client.chat.completions.create')
    async def test_generate_scene_descriptions(self, mock_openai, sample_scene):
        """Test scene description generation."""
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Panel description with visual details"
        mock_openai.return_value = mock_response
        
        agent = VisualDescriptionAgent()
        
        updated_scene = await agent.generate_scene_descriptions(sample_scene)
        
        assert len(updated_scene.panels) > 0, "Should have panels"
        for panel in updated_scene.panels:
            assert panel.visual_description, f"Panel should have visual description: {panel}"


class TestImageGenerationCoordinator:
    """Test image generation (with mocking)."""
    
    @patch('agents.image_generator.openai_client.images.generate')
    async def test_generate_panel_image(self, mock_openai):
        """Test panel image generation."""
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.data = [Mock()]
        mock_response.data[0].url = "https://example.com/test-image.png"
        mock_openai.return_value = mock_response
        
        coordinator = ImageGenerationCoordinator(Path("test_output"))
        
        panel = Panel(
            events=[],
            panel_type="action",
            description="Test panel",
            visual_description="A detailed visual description"
        )
        
        with patch('agents.image_generator.httpx.AsyncClient') as mock_client:
            # Mock image download
            mock_client.return_value.__aenter__.return_value.get.return_value.content = b"fake_image_data"
            
            result = await coordinator.generate_panel_image(panel, "test_scene")
        
        assert result.success, "Image generation should succeed"
        assert result.local_path, "Should have local path"


class TestFullPipeline:
    """Integration tests for the full pipeline."""
    
    @patch('agents.visual_description.openai_client.chat.completions.create')
    @patch('agents.image_generator.openai_client.images.generate')
    async def test_full_mission_processing(self, mock_image_gen, mock_descriptions):
        """Test processing a full mission."""
        # Mock OpenAI responses
        mock_desc_response = Mock()
        mock_desc_response.choices = [Mock()]
        mock_desc_response.choices[0].message.content = "Detailed panel description"
        mock_descriptions.return_value = mock_desc_response
        
        mock_img_response = Mock()
        mock_img_response.data = [Mock()]
        mock_img_response.data[0].url = "https://example.com/test.png"
        mock_image_gen.return_value = mock_img_response
        
        # Mock image download
        with patch('agents.image_generator.httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get.return_value.content = b"fake_image"
            
            generator = ComicBookGenerator(Path("test_output"))
            
            # Test with mission1 if available
            mission1_path = Path("data/mission1")
            if mission1_path.exists():
                mission = await generator.generate_comic_from_mission(mission1_path)
                
                assert mission.characters, "Should have characters"
                assert mission.scenes, "Should have scenes"
                assert mission.pages, "Should have pages"
                
                print(f"Generated comic:")
                print(f"  Characters: {len(mission.characters)}")
                print(f"  Scenes: {len(mission.scenes)}")
                print(f"  Pages: {len(mission.pages)}")
                print(f"  Total panels: {sum(len(p.panels) for p in mission.pages)}")
            else:
                pytest.skip("Mission 1 data not available")


async def run_manual_tests():
    """Run tests manually without pytest."""
    print("=== D&D Comic Generator Tests ===\n")
    
    # Test data parsing
    print("1. Testing Data Parsing...")
    try:
        parser = DataParsingAgent()
        
        # Test with mission1 data
        mission1_path = Path("data/mission1")
        if mission1_path.exists():
            char_file = mission1_path / "mission1_chars.txt"
            ic_file = mission1_path / "mission1_ic.txt"
            
            if char_file.exists():
                chars_content = char_file.read_text(encoding='utf-8')
                characters = await parser.parse_characters(chars_content)
                print(f"   ✓ Parsed {len(characters)} characters")
                for char in characters[:3]:
                    print(f"     - {char.name} ({char.char_class})")
            
            if ic_file.exists():
                ic_content = ic_file.read_text(encoding='utf-8')
                events = await parser.parse_ic_logs(ic_content)
                print(f"   ✓ Parsed {len(events)} events")
                print(f"     - First event: {events[0].character_name if events else 'None'}")
        else:
            print("   ⚠ Mission 1 data not found, skipping")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Test scene planning
    print("\n2. Testing Scene Planning...")
    try:
        if 'events' in locals() and events:
            planner = ScenePlanningAgent()
            scenes = await planner.plan_comic_structure(events[:10])  # Use first 10 events
            print(f"   ✓ Created {len(scenes)} scenes")
            
            total_panels = sum(len(scene.panels) for scene in scenes)
            print(f"   ✓ Generated {total_panels} panels")
        else:
            print("   ⚠ No events available for testing")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Test visual descriptions (mocked)
    print("\n3. Testing Visual Descriptions...")
    try:
        with patch('agents.visual_description.openai_client.chat.completions.create') as mock_openai:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "A detailed fantasy scene"
            mock_openai.return_value = mock_response
            
            agent = VisualDescriptionAgent()
            if 'scenes' in locals() and scenes:
                updated_scene = await agent.generate_scene_descriptions(scenes[0])
                print(f"   ✓ Generated descriptions for {len(updated_scene.panels)} panels")
            else:
                print("   ⚠ No scenes available for testing")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    print("\n=== Tests Complete ===")
    print("\nTo run full pipeline:")
    print("python cli.py generate data/mission1")


if __name__ == "__main__":
    # Run manual tests
    asyncio.run(run_manual_tests())
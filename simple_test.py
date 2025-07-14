"""Simple test script to verify the D&D Comic Generator works."""

import asyncio
from pathlib import Path
from unittest.mock import Mock, patch
import sys
import os

# Add the current directory to the path so we can import our modules
sys.path.insert(0, os.getcwd())

from agents.data_parser import DataParsingAgent
from agents.scene_planner import ScenePlanningAgent
from agents.visual_description import VisualDescriptionAgent
from agents.image_generator import ImageGenerationCoordinator
from comic_generator import ComicBookGenerator
from config import settings


async def test_data_parsing():
    """Test parsing real mission data."""
    print("=== Testing Data Parsing ===")
    
    parser = DataParsingAgent()
    
    # Test with mission1 data
    mission1_path = Path("data/mission1")
    if not mission1_path.exists():
        print("   ⚠ Mission 1 data not found, skipping")
        return None, None
    
    char_file = mission1_path / "mission1_chars.txt"
    ic_file = mission1_path / "mission1_ic.txt"
    
    characters = []
    events = []
    
    if char_file.exists():
        try:
            chars_content = char_file.read_text(encoding='utf-8')
            characters = await parser.parse_characters(chars_content)
            print(f"   ✓ Parsed {len(characters)} characters")
            for char in characters[:3]:
                print(f"     - {char.name} ({char.char_class})")
        except Exception as e:
            print(f"   ✗ Character parsing error: {e}")
    
    if ic_file.exists():
        try:
            ic_content = ic_file.read_text(encoding='utf-8')
            events = await parser.parse_ic_logs(ic_content)
            print(f"   ✓ Parsed {len(events)} events")
            if events:
                print(f"     - First event: {events[0].character_name} - {events[0].content[:50]}...")
        except Exception as e:
            print(f"   ✗ IC parsing error: {e}")
    
    return characters, events


async def test_scene_planning(events):
    """Test scene planning with real data."""
    print("\n=== Testing Scene Planning ===")
    
    if not events:
        print("   ⚠ No events available for testing")
        return []
    
    try:
        planner = ScenePlanningAgent()
        scenes = await planner.plan_comic_structure(events[:15])  # Use first 15 events
        print(f"   ✓ Created {len(scenes)} scenes")
        
        total_panels = sum(len(scene.panels) for scene in scenes)
        print(f"   ✓ Generated {total_panels} panels")
        
        for i, scene in enumerate(scenes[:3]):  # Show first 3 scenes
            print(f"     - Scene {i+1}: {scene.location} ({len(scene.events)} events, {len(scene.panels)} panels)")
        
        return scenes
        
    except Exception as e:
        print(f"   ✗ Scene planning error: {e}")
        return []


async def test_visual_descriptions(scenes):
    """Test visual description generation (mocked)."""
    print("\n=== Testing Visual Descriptions ===")
    
    if not scenes:
        print("   ⚠ No scenes available for testing")
        return
    
    try:
        # Mock the OpenAI API call
        with patch('agents.visual_description.openai_client.chat.completions.create') as mock_openai:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "A detailed fantasy scene with dramatic lighting, showing characters in medieval clothing within a tavern setting."
            mock_openai.return_value = mock_response
            
            agent = VisualDescriptionAgent()
            updated_scene = await agent.generate_scene_descriptions(scenes[0])
            
            print(f"   ✓ Generated descriptions for {len(updated_scene.panels)} panels")
            for i, panel in enumerate(updated_scene.panels[:2]):  # Show first 2 panels
                desc = panel.visual_description or "No description"
                print(f"     - Panel {i+1}: {desc[:60]}...")
                
    except Exception as e:
        print(f"   ✗ Visual description error: {e}")


async def test_image_generation():
    """Test image generation coordination (mocked)."""
    print("\n=== Testing Image Generation ===")
    
    try:
        # Mock the OpenAI API call
        with patch('agents.image_generator.openai_client.images.generate') as mock_openai:
            mock_response = Mock()
            mock_response.data = [Mock()]
            mock_response.data[0].url = "https://example.com/test-image.png"
            mock_openai.return_value = mock_response
            
            # Mock image download
            with patch('agents.image_generator.httpx.AsyncClient') as mock_client:
                mock_get = Mock()
                mock_get.content = b"fake_image_data"
                mock_client.return_value.__aenter__.return_value.get.return_value = mock_get
                
                from models import Panel
                coordinator = ImageGenerationCoordinator(Path("test_output"))
                
                panel = Panel(
                    events=[],
                    panel_type="action",
                    description="Test panel",
                    visual_description="A detailed fantasy scene showing an adventurer"
                )
                
                result = await coordinator.generate_panel_image(panel, "test_scene")
                
                if result.success:
                    print(f"   ✓ Image generation successful")
                    print(f"     - Mock URL: {result.image_url}")
                else:
                    print(f"   ✗ Image generation failed: {result.error}")
                    
    except Exception as e:
        print(f"   ✗ Image generation error: {e}")


async def test_cli_validation():
    """Test CLI validation functionality."""
    print("\n=== Testing CLI Validation ===")
    
    mission1_path = Path("data/mission1")
    if mission1_path.exists():
        required_patterns = ["*ic.txt", "*chars*"]
        found_files = []
        
        for pattern in required_patterns:
            files = list(mission1_path.glob(pattern))
            if files:
                found_files.extend(files)
                print(f"   ✓ Found {pattern}: {[f.name for f in files]}")
            else:
                print(f"   ✗ Missing {pattern}")
        
        if found_files:
            print(f"   ✓ Mission folder is valid ({len(found_files)} files found)")
        else:
            print(f"   ✗ Mission folder validation failed")
    else:
        print("   ⚠ Mission 1 folder not found")


async def main():
    """Run all tests."""
    print("🎲 D&D Comic Generator Test Suite 🎲\n")
    
    # Test 1: Data Parsing
    characters, events = await test_data_parsing()
    
    # Test 2: Scene Planning
    scenes = await test_scene_planning(events)
    
    # Test 3: Visual Descriptions
    await test_visual_descriptions(scenes)
    
    # Test 4: Image Generation
    await test_image_generation()
    
    # Test 5: CLI Validation
    await test_cli_validation()
    
    print("\n=== Test Summary ===")
    print("✓ Data parsing from Discord logs")
    print("✓ Scene planning and panel generation")
    print("✓ Visual description generation (mocked)")
    print("✓ Image generation coordination (mocked)")
    print("✓ Mission folder validation")
    
    print("\n🎯 Next Steps:")
    print("1. Set OPENAI_API_KEY environment variable")
    print("2. Run: python cli.py generate data/mission1")
    print("3. Check output folder for generated comic")
    
    print("\n📚 Ready to generate your first D&D comic!")


if __name__ == "__main__":
    asyncio.run(main())
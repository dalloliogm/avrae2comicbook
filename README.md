# D&D Comic Book Generator

Transform your Dungeons & Dragons play-by-post game logs into beautiful comic books using AI!

## Overview

This LLM Agentic system converts Discord-based D&D game logs into comic book format by analyzing character interactions, dialogue, and actions to create a visual narrative. The system uses multiple specialized AI agents to parse data, plan scenes, generate visual descriptions, and coordinate image generation.

## Features

- **Multi-Agent Architecture**: Specialized agents for different processing stages
- **Discord Log Parsing**: Processes timestamped chat logs from multiple channels
- **Character Continuity**: Maintains character appearance and personality across panels
- **Scene Planning**: Intelligently groups events into dramatic comic scenes
- **Visual Generation**: Creates detailed prompts for AI image generation
- **Comic Layout**: Organizes panels into properly formatted comic pages
- **Multiple Output Formats**: Generates markdown reports, image files, and metadata

## Architecture

```
Discord Logs → Data Parser → Scene Planner → Visual Description → Image Generation → Comic Layout
```

### Core Agents

1. **Data Parsing Agent**: Extracts characters, events, and metadata from Discord logs
2. **Scene Planning Agent**: Groups events into scenes and plans panel layouts
3. **Character Continuity Agent**: Maintains consistent character descriptions
4. **Visual Description Agent**: Generates detailed visual prompts for each panel
5. **Image Generation Coordinator**: Manages AI image generation with multiple providers
6. **Layout & Composition Agent**: Arranges panels and adds text overlays
7. **Quality Review Agent**: Ensures consistency and quality across the comic

## Installation

1. **Clone the repository**:
```bash
git clone <repository-url>
cd avrae2comicbook
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Set up environment variables**:
```bash
# Required
export OPENAI_API_KEY="your-openai-api-key"

# Optional
export ANTHROPIC_API_KEY="your-anthropic-key"
export STABILITY_API_KEY="your-stability-key"
```

4. **Setup and test**:
```bash
python cli.py setup
```

## Usage

### Command Line Interface

#### Generate Single Comic
```bash
python cli.py generate data/mission1 --output comics/
```

#### Batch Generate Comics
```bash
python cli.py batch data/ --output comics/
```

#### Validate Mission Data
```bash
python cli.py validate data/mission1
```

#### Setup Environment
```bash
python cli.py setup
```

### Mission Folder Structure

Your mission folders should contain D&D game logs with this structure:

```
mission1/
├── mission1_chars.txt    # Character sheets and descriptions
├── mission1_ic.txt       # In-character dialogue and actions
├── mission1_ooc.txt      # Out-of-character context (optional)
└── mission1_rolls.txt    # Dice rolls and mechanics (optional)
```

#### File Format Examples

**Character File (`*_chars.txt`)**:
```
**Eldara Moonwhisper**
- **Race**: Half-Elf
- **Class**: Ranger
- **Appearance**: Silver hair, green eyes, leather armor
- **Equipment**: Longbow, twin daggers, healing potions

**Thorin Ironforge**
- **Race**: Dwarf  
- **Class**: Fighter
- **Appearance**: Red beard, plate armor, battle axe
```

**IC Logs (`*_ic.txt`)**:
```
[2024-01-15 14:30] Eldara: *draws her bow and nocks an arrow* 
"Goblins ahead, everyone stay quiet"

[2024-01-15 14:31] Thorin: *hefts his battle axe* 
"Quiet? I'll show them quiet!" *charges forward*

[2024-01-15 14:32] DM: The goblins screech in alarm as Thorin crashes through the undergrowth...
```

### Programmatic Usage

```python
from comic_generator import ComicBookGenerator
from pathlib import Path

async def generate_comic():
    generator = ComicBookGenerator(Path("output"))
    mission = await generator.generate_comic_from_mission(Path("data/mission1"))
    
    print(f"Generated comic with {len(mission.pages)} pages")
    print(f"Characters: {[c.name for c in mission.characters]}")
```

## Output

The generator creates several outputs:

### Generated Files
```
output/
└── mission1_20240115/
    ├── summary_report.md           # Mission overview and statistics
    ├── panel_descriptions.md       # Detailed panel descriptions
    ├── character_profiles.json     # Character data and descriptions
    ├── scene_breakdown.json       # Scene structure and timing
    ├── images/
    │   ├── scene_01_panel_01.png
    │   ├── scene_01_panel_02.png
    │   └── ...
    └── metadata/
        ├── mission_data.json       # Complete mission structure
        └── generation_log.txt      # Processing log
```

### Summary Report
- Character introductions and descriptions
- Scene-by-scene breakdown
- Panel counts and composition analysis
- Key moments and dramatic beats

### Panel Descriptions
- Detailed visual descriptions for each panel
- Character positioning and expressions
- Environment and lighting details
- Action sequences and effects

## Configuration

Edit [`config.py`](config.py) to customize:

```python
# Image generation settings
MAX_PANELS_PER_PAGE = 6
IMAGE_SIZE = "1024x1024"
IMAGE_STYLE = "fantasy art, comic book style"

# Processing limits
MAX_CONCURRENT_REQUESTS = 3
REQUEST_DELAY = 1.0

# Output settings
GENERATE_IMAGES = True
SAVE_METADATA = True
```

## Testing

Run the test suite:

```bash
# Run all tests
python test_comic_generator.py

# Run with pytest (if installed)
pytest test_comic_generator.py -v

# Test specific components
python -c "from test_comic_generator import run_manual_tests; import asyncio; asyncio.run(run_manual_tests())"
```

## API Integration

### Supported Image Providers

1. **OpenAI DALL-E 3** (Primary)
   - High quality fantasy art generation
   - Good character consistency
   - Rate limits: 50 requests/day

2. **Stability AI** (Fallback)
   - Fast generation times
   - Customizable styles
   - Higher rate limits

3. **Anthropic Claude** (Text descriptions)
   - Enhanced visual descriptions
   - Character analysis
   - Scene planning assistance

### Adding New Providers

Extend the [`ImageGenerationCoordinator`](agents/image_generator.py):

```python
async def generate_with_custom_api(self, prompt: str) -> ImageGenerationResult:
    # Implement your custom image generation logic
    pass
```

## Troubleshooting

### Common Issues

**Missing API Key**:
```bash
Error: OpenAI API key not found!
```
Solution: Set the `OPENAI_API_KEY` environment variable

**Invalid Mission Format**:
```bash
Error: No D&D log files found in 'mission_folder'!
```
Solution: Ensure your mission folder contains `*ic.txt` and `*chars*` files

**Rate Limit Errors**:
```bash
Error: Rate limit exceeded
```
Solution: Increase `REQUEST_DELAY` in config.py or try again later

### Debug Mode

Enable verbose logging:
```bash
python cli.py generate data/mission1 --verbose
```

### Manual Testing

Test individual components:
```python
from agents.data_parser import DataParsingAgent
import asyncio

async def test_parsing():
    parser = DataParsingAgent()
    with open("data/mission1/mission1_chars.txt") as f:
        characters = await parser.parse_characters(f.read())
    print(f"Parsed {len(characters)} characters")

asyncio.run(test_parsing())
```

## Roadmap

### Phase 1 (Current)
- ✅ Data parsing from Discord logs
- ✅ Scene planning and panel generation
- ✅ Visual description generation
- ✅ Image generation coordination
- ✅ Basic CLI interface

### Phase 2 (Planned)
- [ ] Advanced panel layout system
- [ ] Text overlay and speech bubbles
- [ ] Character emotion tracking
- [ ] Multiple comic styles
- [ ] Web interface

### Phase 3 (Future)
- [ ] Real-time Discord bot integration
- [ ] Video generation capabilities
- [ ] Interactive comic viewer
- [ ] Community sharing platform

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

### Development Setup

```bash
# Install development dependencies
pip install -r requirements.txt
pip install pytest black flake8

# Run code formatting
black .

# Run linting
flake8 .

# Run tests
pytest
```

## License

MIT License - see LICENSE file for details.

## Support

- Create an issue for bug reports
- Join our Discord for community support
- Check the documentation for detailed guides

## Examples

See the [`data/`](data/) directory for example mission formats and expected outputs.

---

**Happy Gaming!** 🎲⚔️📚

Transform your epic D&D adventures into visual stories that capture every heroic moment, dramatic dialogue, and spectacular battle!
"""Data Parsing Agent for converting Discord logs into knowledge graph format."""

import re
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import pandas as pd
from loguru import logger

from models import (
    Character, Location, Event, Mission, EventType, CharacterClass,
    ProcessingStatus
)


class DataParsingAgent:
    """Agent responsible for parsing Discord logs into structured format."""
    
    def __init__(self):
        self.characters: Dict[str, Character] = {}
        self.locations: Dict[str, Location] = {}
        self.events: List[Event] = []
        self.current_mission: Optional[Mission] = None
        
    def parse_mission(self, mission_folder: Path) -> Mission:
        """Parse a complete mission from folder containing all channel logs."""
        mission_id = mission_folder.name
        logger.info(f"Starting to parse mission: {mission_id}")
        
        # Initialize mission
        mission = Mission(
            id=mission_id,
            title=f"Mission {mission_id}",
            session_date=datetime.now(),  # Will be extracted from logs
            characters=[],
            locations=[],
            events=[],
            scenes=[],
            pages=[]
        )
        
        self.current_mission = mission
        
        # Parse different channel types
        self._parse_character_files(mission_folder)
        self._parse_ic_logs(mission_folder)
        self._parse_ooc_logs(mission_folder)
        self._parse_rolls_logs(mission_folder)
        
        # Finalize mission data
        mission.characters = list(self.characters.values())
        mission.locations = list(self.locations.values())
        mission.events = self.events
        
        logger.info(f"Parsed mission {mission_id}: {len(mission.characters)} characters, "
                   f"{len(mission.events)} events, {len(mission.locations)} locations")
        
        return mission
        
    def _parse_character_files(self, mission_folder: Path) -> None:
        """Parse character description files."""
        char_files = list(mission_folder.glob("*chars*"))
        
        for char_file in char_files:
            logger.info(f"Parsing character file: {char_file.name}")
            
            if char_file.suffix == '.md':
                self._parse_markdown_characters(char_file)
            else:
                self._parse_text_characters(char_file)
                
    def _parse_markdown_characters(self, char_file: Path) -> None:
        """Parse character data from markdown files."""
        content = char_file.read_text(encoding='utf-8')
        
        # Split by character entries (look for character names in headers)
        character_blocks = re.split(r'\n(?=\w+\s*\([\w\s]+\))', content)
        
        for block in character_blocks:
            if not block.strip():
                continue
                
            char_data = self._extract_character_from_markdown(block)
            if char_data:
                self.characters[char_data.id] = char_data
                
    def _extract_character_from_markdown(self, block: str) -> Optional[Character]:
        """Extract character data from markdown block."""
        lines = block.split('\n')
        
        # Find character name and player
        name_match = re.search(r'^(\w+)\s*\(([^)]+)\)', lines[0])
        if not name_match:
            return None
            
        char_name = name_match.group(1)
        player_name = name_match.group(2)
        
        # Extract basic info
        race = None
        char_class = None
        level = None
        description = None
        
        for line in lines:
            if 'Race:' in line or 'Humanoid' in line:
                race_match = re.search(r'(?:Race:|Humanoid \()([^)]+)', line)
                if race_match:
                    race = race_match.group(1).strip()
                    
            if 'Class:' in line:
                class_match = re.search(r'Class:\s*([^/\s]+)', line)
                if class_match:
                    char_class = class_match.group(1).lower()
                    
            if 'Level:' in line:
                level_match = re.search(r'Level:\s*(\d+)', line)
                if level_match:
                    level = int(level_match.group(1))
                    
            if 'Description:' in line:
                desc_start = lines.index(line) + 1
                desc_lines = []
                for desc_line in lines[desc_start:]:
                    if desc_line.strip() and not desc_line.startswith('Image'):
                        desc_lines.append(desc_line)
                    else:
                        break
                description = '\n'.join(desc_lines).strip()
                
        # Extract stats and equipment
        stats = self._extract_stats_from_block(block)
        equipment = self._extract_equipment_from_block(block)
        
        return Character(
            id=char_name.lower(),
            name=char_name,
            player_name=player_name,
            race=race,
            character_class=char_class,
            level=level,
            description=description,
            stats=stats,
            equipment=equipment
        )
        
    def _extract_stats_from_block(self, block: str) -> Dict[str, any]:
        """Extract character stats from text block."""
        stats = {}
        
        # Look for ability scores
        ability_match = re.search(r'STR:\s*(\d+)\s*\([^)]+\)\s*DEX:\s*(\d+)\s*\([^)]+\)\s*CON:\s*(\d+)\s*\([^)]+\)\s*INT:\s*(\d+)\s*\([^)]+\)\s*WIS:\s*(\d+)\s*\([^)]+\)\s*CHA:\s*(\d+)', block)
        if ability_match:
            stats.update({
                'strength': int(ability_match.group(1)),
                'dexterity': int(ability_match.group(2)),
                'constitution': int(ability_match.group(3)),
                'intelligence': int(ability_match.group(4)),
                'wisdom': int(ability_match.group(5)),
                'charisma': int(ability_match.group(6))
            })
            
        # Look for AC, HP, etc.
        ac_match = re.search(r'AC:\s*(\d+)', block)
        if ac_match:
            stats['armor_class'] = int(ac_match.group(1))
            
        hp_match = re.search(r'HP:\s*(\d+)/(\d+)', block)
        if hp_match:
            stats['hit_points'] = int(hp_match.group(1))
            stats['max_hit_points'] = int(hp_match.group(2))
            
        return stats
        
    def _extract_equipment_from_block(self, block: str) -> List[str]:
        """Extract equipment list from text block."""
        equipment = []
        
        # Look for magic items section
        magic_items_match = re.search(r'Magic Items:\s*([^\n]+)', block)
        if magic_items_match:
            items_text = magic_items_match.group(1)
            equipment.extend([item.strip() for item in items_text.split(',')])
            
        # Look for attacks section for weapons
        attacks_section = re.search(r'Attacks\n(.*?)(?=\n\w+:|$)', block, re.DOTALL)
        if attacks_section:
            attacks_text = attacks_section.group(1)
            weapon_matches = re.findall(r'^([^:]+):', attacks_text, re.MULTILINE)
            equipment.extend([weapon.strip() for weapon in weapon_matches])
            
        return equipment
        
    def _parse_text_characters(self, char_file: Path) -> None:
        """Parse character data from text files."""
        content = char_file.read_text(encoding='utf-8')
        
        # Similar parsing logic for .txt files
        # This is a simplified version - can be expanded
        lines = content.split('\n')
        current_char = None
        
        for line in lines:
            if '(' in line and ')' in line and not line.strip().startswith('!'):
                # Potential character name line
                name_match = re.search(r'^(\w+)\s*\(([^)]+)\)', line)
                if name_match and current_char is None:
                    char_name = name_match.group(1)
                    player_name = name_match.group(2)
                    
                    current_char = Character(
                        id=char_name.lower(),
                        name=char_name,
                        player_name=player_name
                    )
                    self.characters[current_char.id] = current_char
                    
    def _parse_ic_logs(self, mission_folder: Path) -> None:
        """Parse in-character logs for dialogue and actions."""
        ic_files = list(mission_folder.glob("*ic.txt"))
        
        for ic_file in ic_files:
            logger.info(f"Parsing IC file: {ic_file.name}")
            self._parse_ic_file(ic_file)
            
    def _parse_ic_file(self, ic_file: Path) -> None:
        """Parse individual IC file."""
        content = ic_file.read_text(encoding='utf-8')
        lines = content.split('\n')
        
        current_event = None
        event_counter = 0
        
        for line in lines:
            if not line.strip():
                continue
                
            # Check for timestamp and speaker
            timestamp_match = re.search(r'(\w+)\s*\([^)]+\)\s*—\s*(\d+/\d+/\d+\s+\d+:\d+\s*[AP]M)', line)
            if timestamp_match:
                speaker = timestamp_match.group(1)
                timestamp_str = timestamp_match.group(2)
                
                # Parse timestamp
                try:
                    timestamp = datetime.strptime(timestamp_str, '%m/%d/%Y %I:%M %p')
                except ValueError:
                    timestamp = datetime.now()
                
                # Start new event
                event_counter += 1
                current_event = Event(
                    id=f"event_{event_counter}",
                    timestamp=timestamp,
                    event_type=EventType.DIALOGUE,
                    description=line,
                    speaker_id=speaker.lower() if speaker.lower() in self.characters else None,
                    participants=[speaker.lower()] if speaker.lower() in self.characters else []
                )
                
                self.events.append(current_event)
                
            elif current_event and line.strip():
                # Continue current event with additional content
                current_event.description += f"\n{line}"
                current_event.dialogue_content = line.strip()
                
                # Determine event type based on content
                if any(keyword in line.lower() for keyword in ['attack', 'cast', 'move', 'action']):
                    current_event.event_type = EventType.ACTION
                elif any(keyword in line.lower() for keyword in ['roll', 'dice', 'd20']):
                    current_event.event_type = EventType.ROLL
                elif line.startswith('"') or 'says' in line.lower():
                    current_event.event_type = EventType.DIALOGUE
                    
    def _parse_ooc_logs(self, mission_folder: Path) -> None:
        """Parse out-of-character logs for context."""
        ooc_files = list(mission_folder.glob("*ooc*"))
        
        for ooc_file in ooc_files:
            logger.info(f"Parsing OOC file: {ooc_file.name}")
            # OOC parsing - mainly for context, not included in final comic
            # This helps understand player intent and clarifications
            
    def _parse_rolls_logs(self, mission_folder: Path) -> None:
        """Parse roll logs for combat mechanics."""
        roll_files = list(mission_folder.glob("*rolls*"))
        
        for roll_file in roll_files:
            logger.info(f"Parsing rolls file: {roll_file.name}")
            self._parse_roll_file(roll_file)
            
    def _parse_roll_file(self, roll_file: Path) -> None:
        """Parse individual roll file."""
        content = roll_file.read_text(encoding='utf-8')
        lines = content.split('\n')
        
        event_counter = len(self.events)
        
        for line in lines:
            if not line.strip():
                continue
                
            # Look for roll results
            roll_match = re.search(r'(\w+)\s*\([^)]+\)\s*—.*?(\d+/\d+/\d+\s+\d+:\d+\s*[AP]M)', line)
            if roll_match:
                speaker = roll_match.group(1)
                timestamp_str = roll_match.group(2)
                
                try:
                    timestamp = datetime.strptime(timestamp_str, '%m/%d/%Y %I:%M %p')
                except ValueError:
                    timestamp = datetime.now()
                
                event_counter += 1
                roll_event = Event(
                    id=f"roll_{event_counter}",
                    timestamp=timestamp,
                    event_type=EventType.ROLL,
                    description=line,
                    speaker_id=speaker.lower() if speaker.lower() in self.characters else None,
                    participants=[speaker.lower()] if speaker.lower() in self.characters else [],
                    game_mechanics=self._extract_roll_mechanics(line)
                )
                
                self.events.append(roll_event)
                
    def _extract_roll_mechanics(self, line: str) -> Dict[str, any]:
        """Extract mechanical information from roll line."""
        mechanics = {}
        
        # Look for dice rolls
        dice_match = re.search(r'(\d+d\d+(?:[+-]\d+)?)', line)
        if dice_match:
            mechanics['dice'] = dice_match.group(1)
            
        # Look for results
        result_match = re.search(r'(\d+)\s*(?:hit|damage|total)', line, re.IGNORECASE)
        if result_match:
            mechanics['result'] = int(result_match.group(1))
            
        # Look for attack/damage type
        if 'attack' in line.lower():
            mechanics['type'] = 'attack'
        elif 'damage' in line.lower():
            mechanics['type'] = 'damage'
        elif 'save' in line.lower():
            mechanics['type'] = 'saving_throw'
            
        return mechanics
        
    def get_processing_status(self) -> ProcessingStatus:
        """Get current processing status."""
        if self.current_mission:
            return ProcessingStatus(
                mission_id=self.current_mission.id,
                status="parsing",
                progress=0.5,
                current_step="Parsing Discord logs",
                started_at=datetime.now()
            )
        return ProcessingStatus(
            mission_id="unknown",
            status="idle",
            progress=0.0,
            current_step="Waiting for mission",
            started_at=datetime.now()
        )
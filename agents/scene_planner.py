"""Scene Planning Agent for analyzing events and creating comic book structure."""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import re
from loguru import logger

from models import (
    Mission, Event, Scene, Panel, ComicPage, EventType,
    Character, Location
)


class ScenePlanningAgent:
    """Agent responsible for planning comic book scenes from parsed events."""
    
    def __init__(self):
        self.scenes: List[Scene] = []
        self.pages: List[ComicPage] = []
        self.current_mission: Optional[Mission] = None
        
    def plan_mission_scenes(self, mission: Mission) -> Mission:
        """Plan scenes and comic structure for a mission."""
        self.current_mission = mission
        logger.info(f"Planning scenes for mission: {mission.id}")
        
        # Sort events by timestamp
        sorted_events = sorted(mission.events, key=lambda e: e.timestamp)
        
        # Group events into scenes
        scene_groups = self._group_events_into_scenes(sorted_events)
        
        # Create scene objects
        self.scenes = []
        for i, (scene_info, events) in enumerate(scene_groups):
            scene = self._create_scene_from_events(i, scene_info, events, mission)
            self.scenes.append(scene)
            
        # Plan comic pages from scenes
        self.pages = self._plan_comic_pages(self.scenes, mission)
        
        # Update mission with scenes and pages
        mission.scenes = self.scenes
        mission.pages = self.pages
        
        logger.info(f"Created {len(self.scenes)} scenes and {len(self.pages)} pages")
        return mission
        
    def _group_events_into_scenes(self, events: List[Event]) -> List[Tuple[Dict, List[Event]]]:
        """Group chronological events into logical scenes."""
        if not events:
            return []
            
        scenes = []
        current_scene_events = []
        current_scene_info = {
            'type': 'dialogue',
            'location': None,
            'main_characters': set(),
            'tension_level': 0.0
        }
        
        scene_break_threshold = timedelta(minutes=30)  # Time gap indicating scene break
        
        for i, event in enumerate(events):
            # Check if we should start a new scene
            should_break = False
            
            if current_scene_events:
                # Time-based break
                time_gap = event.timestamp - current_scene_events[-1].timestamp
                if time_gap > scene_break_threshold:
                    should_break = True
                    
                # Location change
                if (event.location_id and current_scene_info['location'] and 
                    event.location_id != current_scene_info['location']):
                    should_break = True
                    
                # Scene type change (dialogue to combat, etc.)
                new_scene_type = self._determine_scene_type(event)
                if new_scene_type != current_scene_info['type']:
                    # Don't break for minor transitions
                    if not (current_scene_info['type'] == 'dialogue' and new_scene_type == 'action'):
                        should_break = True
                        
            if should_break and current_scene_events:
                # Finalize current scene
                scenes.append((current_scene_info.copy(), current_scene_events.copy()))
                current_scene_events = []
                current_scene_info = {
                    'type': 'dialogue',
                    'location': None,
                    'main_characters': set(),
                    'tension_level': 0.0
                }
                
            # Add event to current scene
            current_scene_events.append(event)
            
            # Update scene info
            scene_type = self._determine_scene_type(event)
            current_scene_info['type'] = scene_type
            
            if event.location_id:
                current_scene_info['location'] = event.location_id
                
            if event.speaker_id:
                current_scene_info['main_characters'].add(event.speaker_id)
                
            for participant in event.participants:
                current_scene_info['main_characters'].add(participant)
                
            # Update tension level
            tension = self._calculate_event_tension(event)
            current_scene_info['tension_level'] = max(current_scene_info['tension_level'], tension)
            
        # Add final scene
        if current_scene_events:
            scenes.append((current_scene_info, current_scene_events))
            
        return scenes
        
    def _determine_scene_type(self, event: Event) -> str:
        """Determine the type of scene based on event content."""
        if event.event_type == EventType.COMBAT:
            return 'combat'
        elif event.event_type == EventType.ROLL:
            return 'action'
        elif event.event_type == EventType.DIALOGUE:
            return 'dialogue'
        elif event.event_type == EventType.ACTION:
            # Analyze action content
            if any(keyword in event.description.lower() for keyword in 
                   ['attack', 'cast', 'fight', 'battle', 'damage']):
                return 'combat'
            elif any(keyword in event.description.lower() for keyword in 
                     ['move', 'jump', 'climb', 'run', 'fly']):
                return 'action'
            else:
                return 'dialogue'
        else:
            return 'dialogue'
            
    def _calculate_event_tension(self, event: Event) -> float:
        """Calculate dramatic tension level (0-1) for an event."""
        tension = 0.0
        
        # Base tension by event type
        if event.event_type == EventType.COMBAT:
            tension += 0.8
        elif event.event_type == EventType.ACTION:
            tension += 0.6
        elif event.event_type == EventType.ROLL:
            tension += 0.4
        elif event.event_type == EventType.DIALOGUE:
            tension += 0.2
            
        # Increase tension based on keywords
        description = event.description.lower()
        
        high_tension_keywords = ['death', 'die', 'kill', 'destroy', 'final', 'last']
        medium_tension_keywords = ['attack', 'fight', 'battle', 'danger', 'threat']
        
        for keyword in high_tension_keywords:
            if keyword in description:
                tension += 0.3
                break
                
        for keyword in medium_tension_keywords:
            if keyword in description:
                tension += 0.2
                break
                
        # Check for dramatic dialogue
        if any(marker in description for marker in ['"', 'says', 'shouts', 'whispers']):
            if any(word in description for word in ['no!', 'help!', 'stop!', 'wait!']):
                tension += 0.3
                
        return min(tension, 1.0)
        
    def _create_scene_from_events(self, scene_index: int, scene_info: Dict, 
                                 events: List[Event], mission: Mission) -> Scene:
        """Create a Scene object from grouped events."""
        if not events:
            raise ValueError("Cannot create scene from empty events list")
            
        scene_id = f"scene_{scene_index + 1}"
        
        # Generate scene title
        title = self._generate_scene_title(scene_info, events)
        
        # Generate scene description
        description = self._generate_scene_description(scene_info, events, mission)
        
        # Determine location
        location_id = scene_info.get('location')
        if not location_id:
            # Try to infer from events
            for event in events:
                if event.location_id:
                    location_id = event.location_id
                    break
                    
        # If still no location, create a generic one
        if not location_id:
            location_id = f"location_{scene_index + 1}"
            generic_location = Location(
                id=location_id,
                name="Unknown Location",
                description="Location details not specified"
            )
            mission.locations.append(generic_location)
            
        scene = Scene(
            id=scene_id,
            title=title,
            description=description,
            start_time=events[0].timestamp,
            end_time=events[-1].timestamp,
            location_id=location_id,
            events=[event.id for event in events],
            main_characters=list(scene_info['main_characters']),
            scene_type=scene_info['type'],
            dramatic_tension=scene_info['tension_level']
        )
        
        return scene
        
    def _generate_scene_title(self, scene_info: Dict, events: List[Event]) -> str:
        """Generate an appropriate title for the scene."""
        scene_type = scene_info['type']
        
        if scene_type == 'combat':
            # Look for enemy names or combat description
            for event in events:
                if event.event_type == EventType.COMBAT:
                    # Try to extract enemy name
                    enemy_match = re.search(r'vs\s+(\w+)', event.description)
                    if enemy_match:
                        return f"Battle Against {enemy_match.group(1)}"
                        
                    # Look for specific combat actions
                    if 'kraken' in event.description.lower():
                        return "Battle with the Elder Kraken"
                    elif 'priest' in event.description.lower():
                        return "Confronting the Cultists"
                        
            return "Combat Encounter"
            
        elif scene_type == 'action':
            # Look for specific actions
            for event in events:
                if 'portal' in event.description.lower():
                    return "Through the Portal"
                elif 'ship' in event.description.lower():
                    return "Aboard the Ship"
                elif 'underwater' in event.description.lower():
                    return "Underwater Struggle"
                    
            return "Action Sequence"
            
        elif scene_type == 'dialogue':
            # Look for key dialogue content
            for event in events:
                if event.event_type == EventType.DIALOGUE:
                    if 'greetings' in event.description.lower():
                        return "Mission Briefing"
                    elif 'gibbulous' in event.description.lower():
                        return "Gatekeeper's Instructions"
                        
            return "Character Interaction"
            
        else:
            return f"Scene {scene_info.get('index', 'Unknown')}"
            
    def _generate_scene_description(self, scene_info: Dict, events: List[Event], 
                                   mission: Mission) -> str:
        """Generate a comprehensive description for the scene."""
        descriptions = []
        
        # Add location context
        location_id = scene_info.get('location')
        if location_id:
            location = next((loc for loc in mission.locations if loc.id == location_id), None)
            if location:
                descriptions.append(f"Setting: {location.name}")
                if location.description:
                    descriptions.append(location.description)
                    
        # Add character context
        main_chars = scene_info['main_characters']
        if main_chars:
            char_names = []
            for char_id in main_chars:
                char = next((c for c in mission.characters if c.id == char_id), None)
                if char:
                    char_names.append(char.name)
            if char_names:
                descriptions.append(f"Main characters: {', '.join(char_names)}")
                
        # Add key events summary
        key_events = []
        for event in events:
            if event.event_type in [EventType.COMBAT, EventType.ACTION]:
                key_events.append(event.description.split('\n')[0])  # First line only
            elif event.event_type == EventType.DIALOGUE and event.dialogue_content:
                if len(event.dialogue_content) < 100:
                    key_events.append(f'"{event.dialogue_content}"')
                    
        if key_events:
            descriptions.append("Key events:")
            descriptions.extend(key_events[:3])  # Limit to 3 key events
            
        return '\n'.join(descriptions)
        
    def _plan_comic_pages(self, scenes: List[Scene], mission: Mission) -> List[ComicPage]:
        """Plan comic book pages from scenes."""
        pages = []
        current_page = None
        page_number = 1
        panel_counter = 0
        
        for scene in scenes:
            # Determine how many panels this scene needs
            panels_needed = self._calculate_panels_needed(scene, mission)
            
            # Create panels for this scene
            scene_panels = self._create_panels_for_scene(scene, panels_needed, mission)
            
            for panel in scene_panels:
                # Check if we need a new page
                if (current_page is None or 
                    len(current_page.panels) >= 6 or  # Max panels per page
                    (len(current_page.panels) >= 4 and scene.dramatic_tension > 0.7)):  # High tension gets more space
                    
                    # Start new page
                    current_page = ComicPage(
                        id=f"page_{page_number}",
                        mission_id=mission.id,
                        page_number=page_number,
                        panels=[]
                    )
                    pages.append(current_page)
                    page_number += 1
                    
                panel_counter += 1
                panel.id = f"panel_{panel_counter}"
                current_page.panels.append(panel)
                
        return pages
        
    def _calculate_panels_needed(self, scene: Scene, mission: Mission) -> int:
        """Calculate number of panels needed for a scene."""
        base_panels = 1
        
        # Add panels based on scene type
        if scene.scene_type == 'combat':
            base_panels = 3  # Setup, action, result
        elif scene.scene_type == 'action':
            base_panels = 2  # Setup, action
        elif scene.scene_type == 'dialogue':
            base_panels = 1  # Usually one panel
            
        # Add panels based on number of characters
        if len(scene.main_characters) > 2:
            base_panels += 1
            
        # Add panels based on dramatic tension
        if scene.dramatic_tension > 0.8:
            base_panels += 2  # High tension gets more panels
        elif scene.dramatic_tension > 0.5:
            base_panels += 1
            
        # Add panels based on number of events
        event_count = len(scene.events)
        if event_count > 5:
            base_panels += 1
            
        return min(base_panels, 4)  # Max 4 panels per scene
        
    def _create_panels_for_scene(self, scene: Scene, panel_count: int, 
                                mission: Mission) -> List[Panel]:
        """Create panels for a scene."""
        panels = []
        
        # Get scene events
        scene_events = [e for e in mission.events if e.id in scene.events]
        
        if panel_count == 1:
            # Single panel for the entire scene
            panel = self._create_single_panel(scene, scene_events, mission)
            panels.append(panel)
            
        elif scene.scene_type == 'combat':
            # Combat scene breakdown
            panels.extend(self._create_combat_panels(scene, scene_events, mission, panel_count))
            
        elif scene.scene_type == 'dialogue':
            # Dialogue scene breakdown
            panels.extend(self._create_dialogue_panels(scene, scene_events, mission, panel_count))
            
        else:
            # Action scene breakdown
            panels.extend(self._create_action_panels(scene, scene_events, mission, panel_count))
            
        return panels
        
    def _create_single_panel(self, scene: Scene, events: List[Event], 
                           mission: Mission) -> Panel:
        """Create a single panel representing an entire scene."""
        # Find the most dramatic event
        key_event = max(events, key=lambda e: self._calculate_event_tension(e))
        
        panel = Panel(
            id="temp_id",  # Will be set by caller
            scene_id=scene.id,
            panel_number=1,
            panel_type=self._determine_panel_type(key_event),
            description=scene.description,
            characters=scene.main_characters,
            dialogue=key_event.dialogue_content if key_event.dialogue_content else None,
            narration=f"Scene: {scene.title}"
        )
        
        return panel
        
    def _create_combat_panels(self, scene: Scene, events: List[Event], 
                            mission: Mission, panel_count: int) -> List[Panel]:
        """Create panels for combat scenes."""
        panels = []
        
        # Panel 1: Setup/Initiative
        setup_panel = Panel(
            id="temp_id",
            scene_id=scene.id,
            panel_number=1,
            panel_type="action",
            description="Combat begins",
            characters=scene.main_characters,
            narration="The battle erupts!"
        )
        panels.append(setup_panel)
        
        # Panel 2: Main action
        combat_events = [e for e in events if e.event_type in [EventType.COMBAT, EventType.ACTION]]
        if combat_events:
            main_event = combat_events[len(combat_events)//2]  # Middle event
            action_panel = Panel(
                id="temp_id",
                scene_id=scene.id,
                panel_number=2,
                panel_type="action",
                description=main_event.description,
                characters=scene.main_characters,
                dialogue=main_event.dialogue_content
            )
            panels.append(action_panel)
            
        # Panel 3: Resolution (if we have 3+ panels)
        if panel_count >= 3:
            resolution_panel = Panel(
                id="temp_id",
                scene_id=scene.id,
                panel_number=3,
                panel_type="action",
                description="Combat resolution",
                characters=scene.main_characters,
                narration="The dust settles..."
            )
            panels.append(resolution_panel)
            
        return panels[:panel_count]
        
    def _create_dialogue_panels(self, scene: Scene, events: List[Event], 
                              mission: Mission, panel_count: int) -> List[Panel]:
        """Create panels for dialogue scenes."""
        panels = []
        
        dialogue_events = [e for e in events if e.event_type == EventType.DIALOGUE]
        
        for i in range(min(panel_count, len(dialogue_events))):
            event = dialogue_events[i]
            panel = Panel(
                id="temp_id",
                scene_id=scene.id,
                panel_number=i + 1,
                panel_type="dialogue",
                description=event.description,
                characters=[event.speaker_id] if event.speaker_id else scene.main_characters,
                dialogue=event.dialogue_content
            )
            panels.append(panel)
            
        return panels
        
    def _create_action_panels(self, scene: Scene, events: List[Event], 
                            mission: Mission, panel_count: int) -> List[Panel]:
        """Create panels for action scenes."""
        panels = []
        
        action_events = [e for e in events if e.event_type == EventType.ACTION]
        
        for i in range(min(panel_count, len(action_events))):
            event = action_events[i]
            panel = Panel(
                id="temp_id",
                scene_id=scene.id,
                panel_number=i + 1,
                panel_type="action",
                description=event.description,
                characters=scene.main_characters,
                dialogue=event.dialogue_content,
                narration=f"Action: {event.description.split('.')[0]}"
            )
            panels.append(panel)
            
        return panels
        
    def _determine_panel_type(self, event: Event) -> str:
        """Determine the best panel type for an event."""
        if event.event_type == EventType.DIALOGUE:
            return "dialogue"
        elif event.event_type in [EventType.COMBAT, EventType.ACTION]:
            return "action"
        elif event.event_type == EventType.ROLL:
            return "action"
        else:
            return "dialogue"
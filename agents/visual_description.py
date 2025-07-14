"""Visual Description Agent for generating detailed image prompts."""

from typing import List, Dict, Optional, Tuple
import re
from loguru import logger

from models import (
    Mission, Scene, Panel, Character, Location, Event, EventType
)


class VisualDescriptionAgent:
    """Agent responsible for creating detailed visual prompts for image generation."""
    
    def __init__(self):
        self.character_descriptions: Dict[str, str] = {}
        self.location_descriptions: Dict[str, str] = {}
        self.style_guidelines = {
            'base_style': 'comic book art style, detailed illustration, vibrant colors',
            'character_style': 'fantasy character design, dynamic poses, expressive faces',
            'combat_style': 'action scene, dynamic movement, energy effects',
            'dialogue_style': 'character interaction, emotional expressions, clear composition',
            'environment_style': 'fantasy environment, atmospheric lighting, detailed background'
        }
        
    def generate_panel_prompts(self, mission: Mission) -> Mission:
        """Generate visual prompts for all panels in a mission."""
        logger.info(f"Generating visual prompts for mission: {mission.id}")
        
        # Cache character and location descriptions
        self._cache_descriptions(mission)
        
        # Generate prompts for each panel
        for page in mission.pages:
            for panel in page.panels:
                prompt = self._generate_panel_prompt(panel, mission)
                panel.visual_prompt = prompt
                
        logger.info(f"Generated prompts for {sum(len(p.panels) for p in mission.pages)} panels")
        return mission
        
    def _cache_descriptions(self, mission: Mission) -> None:
        """Cache character and location descriptions for consistent reference."""
        # Cache character descriptions
        for character in mission.characters:
            self.character_descriptions[character.id] = self._create_character_description(character)
            
        # Cache location descriptions
        for location in mission.locations:
            self.location_descriptions[location.id] = self._create_location_description(location)
            
    def _create_character_description(self, character: Character) -> str:
        """Create a detailed visual description for a character."""
        description_parts = []
        
        # Basic identity
        if character.name:
            description_parts.append(f"{character.name}")
            
        # Race and class
        if character.race:
            description_parts.append(f"{character.race}")
        if character.character_class:
            description_parts.append(f"{character.character_class}")
            
        # Physical description from character sheet
        if character.description:
            # Clean and format the description
            clean_desc = re.sub(r'\s+', ' ', character.description.strip())
            description_parts.append(clean_desc)
            
        # Equipment-based visual elements
        if character.equipment:
            weapon_items = []
            armor_items = []
            magic_items = []
            
            for item in character.equipment:
                item_lower = item.lower()
                if any(weapon in item_lower for weapon in ['sword', 'bow', 'staff', 'axe', 'dagger']):
                    weapon_items.append(item)
                elif any(armor in item_lower for armor in ['armor', 'shield', 'helmet', 'cloak']):
                    armor_items.append(item)
                elif any(magic in item_lower for magic in ['ring', 'amulet', 'crystal', 'magical']):
                    magic_items.append(item)
                    
            if weapon_items:
                description_parts.append(f"wielding {', '.join(weapon_items[:2])}")
            if armor_items:
                description_parts.append(f"wearing {', '.join(armor_items[:2])}")
            if magic_items:
                description_parts.append(f"adorned with {', '.join(magic_items[:2])}")
                
        # Class-specific visual elements
        if character.character_class:
            class_visuals = {
                'wizard': 'robes, spellbook, arcane focus',
                'fighter': 'martial stance, battle-worn equipment',
                'rogue': 'leather armor, daggers, stealthy posture',
                'cleric': 'holy symbol, divine aura, healing hands',
                'barbarian': 'tribal markings, fierce expression, primitive weapons',
                'ranger': 'nature-worn clothing, bow, animal companion vibes',
                'paladin': 'shining armor, divine weapon, righteous bearing',
                'sorcerer': 'innate magic aura, elemental effects around hands',
                'warlock': 'dark magic effects, otherworldly patron marks',
                'bard': 'musical instrument, charismatic pose, colorful clothing',
                'druid': 'natural materials, earth tones, connection to nature',
                'monk': 'simple robes, martial arts stance, inner peace'
            }
            if character.character_class in class_visuals:
                description_parts.append(class_visuals[character.character_class])
                
        return ', '.join(description_parts)
        
    def _create_location_description(self, location: Location) -> str:
        """Create a detailed visual description for a location."""
        description_parts = []
        
        if location.name:
            description_parts.append(location.name)
            
        if location.description:
            clean_desc = re.sub(r'\s+', ' ', location.description.strip())
            description_parts.append(clean_desc)
            
        if location.environment_type:
            description_parts.append(f"{location.environment_type} environment")
            
        if location.atmosphere:
            description_parts.append(f"{location.atmosphere} atmosphere")
            
        if location.key_features:
            description_parts.append(f"featuring {', '.join(location.key_features)}")
            
        return ', '.join(description_parts)
        
    def _generate_panel_prompt(self, panel: Panel, mission: Mission) -> str:
        """Generate a comprehensive visual prompt for a panel."""
        prompt_parts = []
        
        # Base style
        prompt_parts.append(self.style_guidelines['base_style'])
        
        # Panel type specific style
        if panel.panel_type == 'combat' or panel.panel_type == 'action':
            prompt_parts.append(self.style_guidelines['combat_style'])
        elif panel.panel_type == 'dialogue':
            prompt_parts.append(self.style_guidelines['dialogue_style'])
        else:
            prompt_parts.append(self.style_guidelines['character_style'])
            
        # Characters in the panel
        if panel.characters:
            character_descs = []
            for char_id in panel.characters:
                if char_id in self.character_descriptions:
                    character_descs.append(self.character_descriptions[char_id])
                else:
                    # Try to find character by name
                    char = next((c for c in mission.characters if c.id == char_id), None)
                    if char:
                        character_descs.append(self._create_character_description(char))
                        
            if character_descs:
                prompt_parts.append(f"Characters: {' and '.join(character_descs)}")
                
        # Scene and location context
        scene = next((s for s in mission.scenes if s.id == panel.scene_id), None)
        if scene:
            if scene.location_id in self.location_descriptions:
                prompt_parts.append(f"Setting: {self.location_descriptions[scene.location_id]}")
                
        # Action description
        if panel.description:
            action_desc = self._enhance_action_description(panel.description, panel.panel_type)
            prompt_parts.append(f"Action: {action_desc}")
            
        # Dialogue visualization
        if panel.dialogue:
            dialogue_visual = self._create_dialogue_visual(panel.dialogue, panel.panel_type)
            if dialogue_visual:
                prompt_parts.append(dialogue_visual)
                
        # Camera angle and composition
        camera_angle = self._determine_camera_angle(panel, scene)
        prompt_parts.append(f"Composition: {camera_angle}")
        
        # Lighting and mood
        lighting = self._determine_lighting(panel, scene)
        prompt_parts.append(f"Lighting: {lighting}")
        
        # Technical specifications
        prompt_parts.append("high quality, detailed, professional comic book illustration")
        
        return ', '.join(prompt_parts)
        
    def _enhance_action_description(self, description: str, panel_type: str) -> str:
        """Enhance action description with visual details."""
        enhanced = description
        
        # Add visual keywords based on panel type
        if panel_type == 'action':
            # Look for action verbs and enhance them
            action_enhancements = {
                'attack': 'dynamic attack motion with weapon trail',
                'cast': 'magical casting pose with spell effects',
                'move': 'fluid movement with motion lines',
                'jump': 'airborne leap with dynamic pose',
                'fight': 'intense combat stance',
                'run': 'running motion with speed lines',
                'fly': 'aerial movement with wind effects'
            }
            
            for action, enhancement in action_enhancements.items():
                if action in enhanced.lower():
                    enhanced = enhanced.replace(action, enhancement)
                    break
                    
        elif panel_type == 'dialogue':
            # Enhance dialogue scenes
            if 'says' in enhanced.lower():
                enhanced += ', speaking gesture, expressive face'
            elif 'whispers' in enhanced.lower():
                enhanced += ', intimate conversation, close positioning'
            elif 'shouts' in enhanced.lower():
                enhanced += ', dramatic gesturing, intense expression'
                
        return enhanced
        
    def _create_dialogue_visual(self, dialogue: str, panel_type: str) -> str:
        """Create visual elements for dialogue."""
        if not dialogue or panel_type != 'dialogue':
            return ""
            
        visual_elements = []
        
        # Determine emotion from dialogue
        dialogue_lower = dialogue.lower()
        
        if any(word in dialogue_lower for word in ['!', 'no!', 'stop!', 'help!']):
            visual_elements.append("dramatic facial expression, intense emotion")
        elif any(word in dialogue_lower for word in ['?', 'what', 'how', 'why']):
            visual_elements.append("questioning expression, curious pose")
        elif any(word in dialogue_lower for word in ['yes', 'good', 'great', 'excellent']):
            visual_elements.append("positive expression, confident posture")
        elif any(word in dialogue_lower for word in ['tired', 'sad', 'sorry', 'afraid']):
            visual_elements.append("melancholic expression, subdued posture")
        else:
            visual_elements.append("natural conversation pose, engaged expression")
            
        return ', '.join(visual_elements)
        
    def _determine_camera_angle(self, panel: Panel, scene: Optional[Scene]) -> str:
        """Determine appropriate camera angle for the panel."""
        if panel.panel_type == 'action':
            if scene and scene.dramatic_tension > 0.7:
                return "dynamic angle, close-up action shot"
            else:
                return "medium shot, action composition"
        elif panel.panel_type == 'dialogue':
            if len(panel.characters) == 1:
                return "medium close-up, character focus"
            elif len(panel.characters) == 2:
                return "two-shot, conversational framing"
            else:
                return "group shot, ensemble composition"
        elif panel.panel_type == 'environment':
            return "wide shot, establishing shot, environmental focus"
        else:
            return "medium shot, balanced composition"
            
    def _determine_lighting(self, panel: Panel, scene: Optional[Scene]) -> str:
        """Determine appropriate lighting for the panel."""
        # Base lighting on scene context
        if scene:
            if scene.location_id:
                if 'underwater' in scene.location_id.lower():
                    return "underwater lighting, filtered blue-green tones"
                elif 'ship' in scene.location_id.lower():
                    return "maritime lighting, deck illumination"
                elif 'gate' in scene.location_id.lower():
                    return "magical portal lighting, mystical glow"
                elif 'cavern' in scene.location_id.lower():
                    return "cave lighting, dramatic shadows"
                    
            # Base on tension level
            if scene.dramatic_tension > 0.8:
                return "dramatic lighting, high contrast, intense shadows"
            elif scene.dramatic_tension > 0.5:
                return "dynamic lighting, moderate contrast"
            else:
                return "natural lighting, balanced exposure"
        else:
            return "standard comic book lighting, clear visibility"
            
    def _extract_scene_context(self, panel: Panel, mission: Mission) -> Dict:
        """Extract additional context from the scene for better prompts."""
        scene = next((s for s in mission.scenes if s.id == panel.scene_id), None)
        if not scene:
            return {}
            
        context = {
            'scene_type': scene.scene_type,
            'tension': scene.dramatic_tension,
            'location': scene.location_id,
            'characters': scene.main_characters
        }
        
        # Get scene events for additional context
        scene_events = [e for e in mission.events if e.id in scene.events]
        
        # Look for environmental cues
        environment_cues = []
        for event in scene_events:
            if 'water' in event.description.lower():
                environment_cues.append('water')
            if 'fire' in event.description.lower():
                environment_cues.append('fire')
            if 'magic' in event.description.lower():
                environment_cues.append('magic')
            if 'blood' in event.description.lower():
                environment_cues.append('blood')
                
        context['environment_cues'] = environment_cues
        
        return context
        
    def update_style_guidelines(self, new_guidelines: Dict[str, str]) -> None:
        """Update style guidelines for different types of panels."""
        self.style_guidelines.update(new_guidelines)
        
    def get_character_consistency_prompt(self, character_id: str) -> str:
        """Get consistency prompt for a specific character."""
        if character_id in self.character_descriptions:
            return f"Character consistency: {self.character_descriptions[character_id]}"
        return ""
"""Main Comic Generator orchestrator that coordinates all agents."""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional
from loguru import logger

from models import Mission, ProcessingStatus
from agents.data_parser import DataParsingAgent
from agents.scene_planner import ScenePlanningAgent
from agents.visual_description import VisualDescriptionAgent
from agents.image_generator import ImageGenerationCoordinator


class ComicBookGenerator:
    """Main orchestrator for the D&D Comic Book Generation system."""
    
    def __init__(self, output_dir: Path = Path("output")):
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)
        
        # Initialize agents
        self.data_parser = DataParsingAgent()
        self.scene_planner = ScenePlanningAgent()
        self.visual_description = VisualDescriptionAgent()
        self.image_generator = ImageGenerationCoordinator(
            output_dir=output_dir / "images"
        )
        
        # Processing status
        self.current_status = ProcessingStatus(
            mission_id="none",
            status="idle",
            progress=0.0,
            current_step="Waiting for mission",
            started_at=datetime.now()
        )
        
    async def generate_comic_from_mission(self, mission_folder: Path) -> Mission:
        """Generate a complete comic book from a mission folder."""
        mission_id = mission_folder.name
        logger.info(f"Starting comic generation for mission: {mission_id}")
        
        self.current_status = ProcessingStatus(
            mission_id=mission_id,
            status="starting",
            progress=0.0,
            current_step="Initializing",
            started_at=datetime.now()
        )
        
        try:
            # Step 1: Parse Discord logs
            logger.info("Step 1: Parsing Discord logs...")
            self.current_status.current_step = "Parsing Discord logs"
            self.current_status.progress = 0.1
            
            mission = self.data_parser.parse_mission(mission_folder)
            
            # Step 2: Plan scenes and comic structure
            logger.info("Step 2: Planning scenes and comic structure...")
            self.current_status.current_step = "Planning scenes"
            self.current_status.progress = 0.3
            
            mission = self.scene_planner.plan_mission_scenes(mission)
            
            # Step 3: Generate visual descriptions
            logger.info("Step 3: Generating visual descriptions...")
            self.current_status.current_step = "Generating visual descriptions"
            self.current_status.progress = 0.5
            
            mission = self.visual_description.generate_panel_prompts(mission)
            
            # Step 4: Generate images
            logger.info("Step 4: Generating images...")
            self.current_status.current_step = "Generating images"
            self.current_status.progress = 0.7
            
            mission = await self.image_generator.generate_all_panel_images(mission)
            
            # Step 5: Finalize and save
            logger.info("Step 5: Finalizing comic...")
            self.current_status.current_step = "Finalizing comic"
            self.current_status.progress = 0.9
            
            # Save mission data
            await self._save_mission_data(mission)
            
            # Mark as completed
            self.current_status.status = "completed"
            self.current_status.progress = 1.0
            self.current_status.current_step = "Complete"
            self.current_status.completed_at = datetime.now()
            
            logger.info(f"Comic generation completed for mission: {mission_id}")
            return mission
            
        except Exception as e:
            logger.error(f"Comic generation failed: {e}")
            self.current_status.status = "failed"
            self.current_status.error_message = str(e)
            raise
            
    async def _save_mission_data(self, mission: Mission) -> None:
        """Save mission data and generate summary files."""
        mission_output_dir = self.output_dir / mission.id
        mission_output_dir.mkdir(exist_ok=True)
        
        # Save mission JSON
        import json
        mission_file = mission_output_dir / "mission_data.json"
        with open(mission_file, 'w', encoding='utf-8') as f:
            json.dump(mission.dict(), f, indent=2, default=str)
            
        # Generate summary report
        await self._generate_summary_report(mission, mission_output_dir)
        
        # Generate panel descriptions file
        await self._generate_panel_descriptions(mission, mission_output_dir)
        
    async def _generate_summary_report(self, mission: Mission, output_dir: Path) -> None:
        """Generate a human-readable summary report."""
        report_file = output_dir / "summary_report.md"
        
        report_lines = [
            f"# Comic Book Generation Report: {mission.title}",
            f"",
            f"**Generated on:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Mission ID:** {mission.id}",
            f"**Session Date:** {mission.session_date.strftime('%Y-%m-%d')}",
            f"",
            f"## Statistics",
            f"- **Characters:** {len(mission.characters)}",
            f"- **Locations:** {len(mission.locations)}",
            f"- **Events:** {len(mission.events)}",
            f"- **Scenes:** {len(mission.scenes)}",
            f"- **Pages:** {len(mission.pages)}",
            f"- **Total Panels:** {sum(len(page.panels) for page in mission.pages)}",
            f"",
            f"## Characters",
        ]
        
        for character in mission.characters:
            report_lines.extend([
                f"### {character.name}",
                f"- **Player:** {character.player_name or 'NPC'}",
                f"- **Race:** {character.race or 'Unknown'}",
                f"- **Class:** {character.character_class or 'Unknown'}",
                f"- **Level:** {character.level or 'Unknown'}",
                f""
            ])
            
        report_lines.extend([
            f"## Scenes",
            f""
        ])
        
        for i, scene in enumerate(mission.scenes, 1):
            report_lines.extend([
                f"### Scene {i}: {scene.title}",
                f"- **Type:** {scene.scene_type}",
                f"- **Duration:** {scene.start_time.strftime('%H:%M')} - {scene.end_time.strftime('%H:%M')}",
                f"- **Tension Level:** {scene.dramatic_tension:.1f}/1.0",
                f"- **Main Characters:** {', '.join(scene.main_characters)}",
                f"- **Events:** {len(scene.events)}",
                f"",
                f"{scene.description}",
                f""
            ])
            
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))
            
    async def _generate_panel_descriptions(self, mission: Mission, output_dir: Path) -> None:
        """Generate detailed panel descriptions for review."""
        panels_file = output_dir / "panel_descriptions.md"
        
        panel_lines = [
            f"# Panel Descriptions: {mission.title}",
            f"",
            f"Detailed descriptions of each comic panel for review and reference.",
            f""
        ]
        
        for page_num, page in enumerate(mission.pages, 1):
            panel_lines.extend([
                f"## Page {page_num}",
                f""
            ])
            
            for panel_num, panel in enumerate(page.panels, 1):
                scene = next((s for s in mission.scenes if s.id == panel.scene_id), None)
                scene_title = scene.title if scene else "Unknown Scene"
                
                panel_lines.extend([
                    f"### Panel {page_num}.{panel_num} - {scene_title}",
                    f"",
                    f"**Type:** {panel.panel_type}",
                    f"**Characters:** {', '.join(panel.characters) if panel.characters else 'None'}",
                    f"",
                    f"**Description:**",
                    f"{panel.description}",
                    f""
                ])
                
                if panel.dialogue:
                    panel_lines.extend([
                        f"**Dialogue:**",
                        f'"{panel.dialogue}"',
                        f""
                    ])
                    
                if panel.narration:
                    panel_lines.extend([
                        f"**Narration:**",
                        f"{panel.narration}",
                        f""
                    ])
                    
                if panel.visual_prompt:
                    panel_lines.extend([
                        f"**Visual Prompt:**",
                        f"{panel.visual_prompt}",
                        f""
                    ])
                    
                if panel.generated_image_path:
                    panel_lines.extend([
                        f"**Generated Image:** `{panel.generated_image_path}`",
                        f""
                    ])
                    
                panel_lines.append("---")
                panel_lines.append("")
                
        with open(panels_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(panel_lines))
            
    def get_processing_status(self) -> ProcessingStatus:
        """Get current processing status."""
        return self.current_status
        
    async def regenerate_images(self, mission: Mission, quality_threshold: float = 0.5) -> Mission:
        """Regenerate low-quality images for a mission."""
        logger.info(f"Regenerating images for mission: {mission.id}")
        
        self.current_status = ProcessingStatus(
            mission_id=mission.id,
            status="regenerating",
            progress=0.0,
            current_step="Regenerating low-quality images",
            started_at=datetime.now()
        )
        
        try:
            mission = await self.image_generator.regenerate_low_quality_images(
                mission, quality_threshold
            )
            
            # Update saved data
            await self._save_mission_data(mission)
            
            self.current_status.status = "completed"
            self.current_status.progress = 1.0
            self.current_status.completed_at = datetime.now()
            
            return mission
            
        except Exception as e:
            logger.error(f"Image regeneration failed: {e}")
            self.current_status.status = "failed"
            self.current_status.error_message = str(e)
            raise
            
    def update_style_guidelines(self, guidelines: dict) -> None:
        """Update visual style guidelines."""
        self.visual_description.update_style_guidelines(guidelines)
        
    def get_generation_statistics(self) -> dict:
        """Get comprehensive generation statistics."""
        return {
            'image_stats': self.image_generator.get_generation_stats(),
            'current_status': self.current_status.dict()
        }


# Convenience functions for common operations
async def generate_comic_from_folder(mission_folder: str, output_dir: str = "output") -> Mission:
    """Generate a comic book from a mission folder (convenience function)."""
    generator = ComicBookGenerator(Path(output_dir))
    return await generator.generate_comic_from_mission(Path(mission_folder))


async def batch_generate_comics(missions_dir: str, output_dir: str = "output") -> list[Mission]:
    """Generate comics for all missions in a directory."""
    missions_path = Path(missions_dir)
    generator = ComicBookGenerator(Path(output_dir))
    
    results = []
    for mission_folder in missions_path.iterdir():
        if mission_folder.is_dir():
            try:
                mission = await generator.generate_comic_from_mission(mission_folder)
                results.append(mission)
            except Exception as e:
                logger.error(f"Failed to process {mission_folder.name}: {e}")
                
    return results


if __name__ == "__main__":
    # Simple test
    import sys
    
    if len(sys.argv) > 1:
        mission_path = sys.argv[1]
        asyncio.run(generate_comic_from_folder(mission_path))
    else:
        print("Usage: python comic_generator.py <mission_folder>")
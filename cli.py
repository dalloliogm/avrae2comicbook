"""Command Line Interface for the D&D Comic Book Generator."""

import asyncio
import typer
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table
from rich.panel import Panel
from loguru import logger
import sys

from comic_generator import ComicBookGenerator, generate_comic_from_folder, batch_generate_comics
from config import settings

app = typer.Typer(help="D&D Comic Book Generator - Transform your game logs into comics!")
console = Console()


@app.command()
def generate(
    mission_folder: str = typer.Argument(..., help="Path to the mission folder containing Discord logs"),
    output_dir: str = typer.Option("output", "--output", "-o", help="Output directory for generated comics"),
    api_key: str = typer.Option(None, "--openai-key", help="OpenAI API key (or set OPENAI_API_KEY env var)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging")
):
    """Generate a comic book from a single mission folder."""
    
    # Setup logging
    if verbose:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")
    else:
        logger.remove()
        logger.add(sys.stderr, level="INFO")
    
    # Set API key if provided
    if api_key:
        settings.openai_api_key = api_key
    
    # Validate inputs
    mission_path = Path(mission_folder)
    if not mission_path.exists():
        console.print(f"[red]Error: Mission folder '{mission_folder}' does not exist![/red]")
        raise typer.Exit(1)
        
    if not mission_path.is_dir():
        console.print(f"[red]Error: '{mission_folder}' is not a directory![/red]")
        raise typer.Exit(1)
        
    # Check for required files
    required_patterns = ["*ic.txt", "*chars*"]
    found_files = []
    for pattern in required_patterns:
        files = list(mission_path.glob(pattern))
        if files:
            found_files.extend(files)
        else:
            console.print(f"[yellow]Warning: No files matching '{pattern}' found in mission folder[/yellow]")
    
    if not found_files:
        console.print(f"[red]Error: No D&D log files found in '{mission_folder}'![/red]")
        console.print("Expected files: *ic.txt (in-character logs), *chars* (character files)")
        raise typer.Exit(1)
    
    # Check API key
    if not settings.openai_api_key:
        console.print("[red]Error: OpenAI API key not found![/red]")
        console.print("Please set OPENAI_API_KEY environment variable or use --openai-key option")
        raise typer.Exit(1)
    
    # Start generation
    console.print(Panel(
        f"[bold blue]Generating Comic Book[/bold blue]\n\n"
        f"Mission: {mission_path.name}\n"
        f"Output: {output_dir}\n"
        f"Files found: {len(found_files)}"
    ))
    
    async def run_generation():
        generator = ComicBookGenerator(Path(output_dir))
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            
            task = progress.add_task("Generating comic...", total=100)
            
            # Monitor progress
            async def update_progress():
                while not progress.tasks[task].finished:
                    status = generator.get_processing_status()
                    progress.update(
                        task, 
                        completed=status.progress * 100,
                        description=status.current_step
                    )
                    await asyncio.sleep(1)
            
            # Start progress monitoring
            progress_task = asyncio.create_task(update_progress())
            
            try:
                # Generate comic
                mission = await generator.generate_comic_from_mission(mission_path)
                progress.update(task, completed=100, description="Complete!")
                progress_task.cancel()
                
                # Display results
                console.print("\n[green]✓ Comic generation completed![/green]")
                
                # Show summary
                table = Table(title="Generation Summary")
                table.add_column("Metric", style="cyan")
                table.add_column("Count", style="green")
                
                table.add_row("Characters", str(len(mission.characters)))
                table.add_row("Scenes", str(len(mission.scenes)))
                table.add_row("Pages", str(len(mission.pages)))
                table.add_row("Panels", str(sum(len(p.panels) for p in mission.pages)))
                
                console.print(table)
                
                # Show output location
                output_path = Path(output_dir) / mission.id
                console.print(f"\n[bold]Output saved to:[/bold] {output_path}")
                console.print(f"[dim]View summary: {output_path / 'summary_report.md'}[/dim]")
                console.print(f"[dim]Panel details: {output_path / 'panel_descriptions.md'}[/dim]")
                
            except Exception as e:
                progress_task.cancel()
                console.print(f"\n[red]✗ Generation failed: {e}[/red]")
                raise typer.Exit(1)
    
    # Run the async function
    asyncio.run(run_generation())


@app.command()
def batch(
    missions_dir: str = typer.Argument(..., help="Directory containing multiple mission folders"),
    output_dir: str = typer.Option("output", "--output", "-o", help="Output directory for generated comics"),
    api_key: str = typer.Option(None, "--openai-key", help="OpenAI API key"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging")
):
    """Generate comics for all missions in a directory."""
    
    # Setup logging
    if verbose:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")
    
    # Set API key if provided
    if api_key:
        settings.openai_api_key = api_key
    
    missions_path = Path(missions_dir)
    if not missions_path.exists():
        console.print(f"[red]Error: Directory '{missions_dir}' does not exist![/red]")
        raise typer.Exit(1)
    
    # Find mission folders
    mission_folders = [d for d in missions_path.iterdir() if d.is_dir()]
    if not mission_folders:
        console.print(f"[red]Error: No subdirectories found in '{missions_dir}'![/red]")
        raise typer.Exit(1)
    
    console.print(f"[blue]Found {len(mission_folders)} mission folders[/blue]")
    
    async def run_batch():
        results = await batch_generate_comics(missions_dir, output_dir)
        
        console.print(f"\n[green]✓ Batch processing completed![/green]")
        console.print(f"Successfully generated {len(results)} comics")
    
    asyncio.run(run_batch())


@app.command()
def validate(
    mission_folder: str = typer.Argument(..., help="Path to mission folder to validate")
):
    """Validate a mission folder structure and contents."""
    
    mission_path = Path(mission_folder)
    if not mission_path.exists():
        console.print(f"[red]Error: '{mission_folder}' does not exist![/red]")
        raise typer.Exit(1)
    
    console.print(f"[blue]Validating mission folder: {mission_path.name}[/blue]")
    
    # Check for expected files
    checks = [
        ("*ic.txt", "In-character logs", True),
        ("*chars*", "Character files", True),
        ("*ooc*", "Out-of-character logs", False),
        ("*rolls*", "Roll logs", False)
    ]
    
    results = []
    for pattern, description, required in checks:
        files = list(mission_path.glob(pattern))
        status = "✓" if files else ("✗" if required else "○")
        color = "green" if files else ("red" if required else "yellow")
        results.append((status, description, len(files), color))
    
    # Display results
    table = Table(title="Validation Results")
    table.add_column("Status", width=8)
    table.add_column("File Type", style="cyan")
    table.add_column("Count", style="white")
    
    for status, desc, count, color in results:
        table.add_row(f"[{color}]{status}[/{color}]", desc, str(count))
    
    console.print(table)
    
    # Overall validation
    required_found = all(count > 0 for _, _, count, _ in results[:2])  # First 2 are required
    if required_found:
        console.print("[green]✓ Mission folder is valid for comic generation![/green]")
    else:
        console.print("[red]✗ Mission folder is missing required files![/red]")
        raise typer.Exit(1)


@app.command()
def setup():
    """Setup and test the comic generator environment."""
    
    console.print("[blue]Setting up D&D Comic Book Generator...[/blue]")
    
    # Check Python version
    import sys
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    console.print(f"Python version: {python_version}")
    
    # Check dependencies
    try:
        import openai
        console.print("[green]✓ OpenAI library available[/green]")
    except ImportError:
        console.print("[red]✗ OpenAI library not found[/red]")
        console.print("Install with: pip install openai")
    
    # Check API key
    if settings.openai_api_key:
        console.print("[green]✓ OpenAI API key configured[/green]")
    else:
        console.print("[yellow]○ OpenAI API key not found[/yellow]")
        console.print("Set OPENAI_API_KEY environment variable")
    
    # Create directories
    for dir_name in ["output", "generated_images", "logs"]:
        dir_path = Path(dir_name)
        dir_path.mkdir(exist_ok=True)
        console.print(f"[green]✓ Created directory: {dir_name}[/green]")
    
    console.print("\n[green]Setup complete![/green]")
    console.print("Use 'python cli.py generate <mission_folder>' to generate your first comic!")


if __name__ == "__main__":
    app()
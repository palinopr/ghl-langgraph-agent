"""
Monitor SQLite checkpoint persistence in production.
Run this after deployment to verify conversations are being saved.
"""
import asyncio
import os
import aiosqlite
from datetime import datetime
from app.utils.simple_logger import get_logger
from rich.console import Console
from rich.table import Table
from rich.live import Live
import time

logger = get_logger("checkpoint_monitor")
console = Console()

async def monitor_checkpoints(db_path: str = "app/checkpoints.db"):
    """Monitor checkpoint database in real-time"""
    
    if not os.path.exists(db_path):
        console.print(f"[red]❌ Database not found at {db_path}[/red]")
        return
    
    console.print(f"[green]✅ Monitoring checkpoint database: {db_path}[/green]")
    console.print(f"[blue]File size: {os.path.getsize(db_path):,} bytes[/blue]\n")
    
    async with aiosqlite.connect(db_path) as db:
        # Get all threads
        async with db.execute("""
            SELECT DISTINCT thread_id, MAX(checkpoint_id) as latest_checkpoint
            FROM checkpoints 
            GROUP BY thread_id
            ORDER BY latest_checkpoint DESC
            LIMIT 20
        """) as cursor:
            threads = await cursor.fetchall()
        
        console.print(f"[cyan]Found {len(threads)} active conversations[/cyan]\n")
        
        # Create monitoring table
        table = Table(title="Active Conversations")
        table.add_column("Contact ID", style="cyan")
        table.add_column("Messages", style="green")
        table.add_column("Last Update", style="yellow")
        table.add_column("Last Message Preview", style="white")
        
        for thread_id, latest_checkpoint in threads:
            # Extract contact ID from thread
            contact_id = thread_id.replace("contact-", "")[:15] + "..."
            
            # Get checkpoint count
            async with db.execute("""
                SELECT COUNT(*) as count
                FROM checkpoints 
                WHERE thread_id = ? 
            """, (thread_id,)) as cursor:
                count_result = await cursor.fetchone()
                checkpoint_count = count_result[0] if count_result else 0
            
            # Get latest checkpoint data
            async with db.execute("""
                SELECT checkpoint, checkpoint_id
                FROM checkpoints 
                WHERE thread_id = ? 
                ORDER BY checkpoint_id DESC 
                LIMIT 1
            """, (thread_id,)) as cursor:
                checkpoint_data = await cursor.fetchone()
            
            if checkpoint_data:
                # Parse checkpoint info
                message_count = str(checkpoint_count)
                last_update = latest_checkpoint[:19] if latest_checkpoint else "Unknown"
                preview = f"Checkpoint: {checkpoint_data[1][:20]}..."
                
                table.add_row(contact_id, message_count, last_update, preview)
        
        console.print(table)

async def watch_checkpoint_growth():
    """Watch database file growth in real-time"""
    db_path = "app/checkpoints.db"
    
    with Live(console=console, refresh_per_second=1) as live:
        last_size = 0
        while True:
            if os.path.exists(db_path):
                current_size = os.path.getsize(db_path)
                growth = current_size - last_size if last_size > 0 else 0
                
                table = Table(title=f"Checkpoint Database Monitor - {datetime.now().strftime('%H:%M:%S')}")
                table.add_column("Metric", style="cyan")
                table.add_column("Value", style="green")
                
                table.add_row("Database Path", db_path)
                table.add_row("File Size", f"{current_size:,} bytes")
                table.add_row("Growth", f"+{growth:,} bytes" if growth > 0 else "0 bytes")
                table.add_row("Status", "🟢 Active" if growth > 0 else "⏸️  Idle")
                
                # Quick thread count
                try:
                    async with aiosqlite.connect(db_path) as db:
                        async with db.execute("SELECT COUNT(DISTINCT thread_id) FROM checkpoints") as cursor:
                            count = await cursor.fetchone()
                            table.add_row("Active Threads", str(count[0]))
                except:
                    table.add_row("Active Threads", "Error reading")
                
                live.update(table)
                last_size = current_size
            
            await asyncio.sleep(5)

async def verify_conversation(contact_id: str):
    """Verify a specific conversation is persisted"""
    db_path = "app/checkpoints.db"
    thread_id = f"contact-{contact_id}"
    
    console.print(f"\n[cyan]Checking conversation for contact: {contact_id}[/cyan]")
    
    async with aiosqlite.connect(db_path) as db:
        async with db.execute("""
            SELECT checkpoint_id, checkpoint_ns
            FROM checkpoints 
            WHERE thread_id = ? 
            ORDER BY checkpoint_id DESC
        """, (thread_id,)) as cursor:
            checkpoints = await cursor.fetchall()
    
    if checkpoints:
        console.print(f"[green]✅ Found {len(checkpoints)} checkpoints[/green]")
        for i, (cp_id, cp_ns) in enumerate(checkpoints[:5]):
            console.print(f"  {i+1}. Checkpoint {cp_id[:40]}... (namespace: {cp_ns})")
    else:
        console.print(f"[red]❌ No checkpoints found for {thread_id}[/red]")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "watch":
            asyncio.run(watch_checkpoint_growth())
        elif sys.argv[1] == "verify" and len(sys.argv) > 2:
            asyncio.run(verify_conversation(sys.argv[2]))
        else:
            asyncio.run(monitor_checkpoints())
    else:
        # Default: show current state
        asyncio.run(monitor_checkpoints())
        console.print("\n[yellow]Usage:[/yellow]")
        console.print("  python monitor_checkpoints.py          # Show current conversations")
        console.print("  python monitor_checkpoints.py watch    # Live monitoring")
        console.print("  python monitor_checkpoints.py verify <contact_id>  # Check specific contact")
#!/usr/bin/env python3
"""
Diagnose thread persistence issues
"""
import sqlite3
import json
from datetime import datetime
import os

def diagnose_thread_persistence():
    """Diagnose thread persistence issues"""
    
    print("🔍 Diagnosing Thread Persistence Issues\n")
    
    db_path = 'app/checkpoints.db'
    
    # Check if database exists
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        print("This means checkpoints aren't being saved at all!")
        return
    
    print(f"✅ Database found at {db_path}")
    print(f"   Size: {os.path.getsize(db_path):,} bytes\n")
    
    # 1. Check database
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all threads
        cursor.execute("""
            SELECT DISTINCT thread_id, COUNT(*) as checkpoints
            FROM checkpoints 
            GROUP BY thread_id
            ORDER BY checkpoints DESC
            LIMIT 10
        """)
        
        threads = cursor.fetchall()
        print(f"📊 Found {len(threads)} conversation threads\n")
        
        for thread_id, count in threads:
            print(f"Thread: {thread_id[:30]}... | Checkpoints: {count}")
        
        # 2. Check latest checkpoint
        cursor.execute("""
            SELECT thread_id, checkpoint, checkpoint_id
            FROM checkpoints 
            ORDER BY checkpoint_id DESC 
            LIMIT 1
        """)
        
        latest = cursor.fetchone()
        if latest:
            thread_id, checkpoint_data, checkpoint_id = latest
            # Handle both string and bytes
            if isinstance(checkpoint_data, bytes):
                checkpoint_data = checkpoint_data.decode('utf-8')
            
            # The checkpoint might be a complex structure, so let's be careful
            print(f"\n📌 Latest Checkpoint:")
            print(f"Thread: {thread_id}")
            print(f"Checkpoint ID: {checkpoint_id}")
            
            # Try to extract meaningful data
            if 'channel_values' in checkpoint_data:
                print("Found channel_values in checkpoint")
            if 'messages' in checkpoint_data:
                print("Found messages in checkpoint")
        
        # 3. Check thread consistency patterns
        print("\n🔍 Thread ID Patterns:")
        cursor.execute("""
            SELECT thread_id FROM checkpoints GROUP BY thread_id
        """)
        all_threads = cursor.fetchall()
        
        conv_threads = [t[0] for t in all_threads if t[0].startswith('conv-')]
        contact_threads = [t[0] for t in all_threads if t[0].startswith('contact-')]
        other_threads = [t[0] for t in all_threads if not (t[0].startswith('conv-') or t[0].startswith('contact-'))]
        
        print(f"- ConversationId-based threads: {len(conv_threads)}")
        print(f"- Contact-based threads: {len(contact_threads)}")
        print(f"- Other format threads: {len(other_threads)}")
        
        if conv_threads:
            print(f"\nExample conversationId thread: {conv_threads[0]}")
        if contact_threads:
            print(f"Example contact-based thread: {contact_threads[0]}")
            
        conn.close()
        
        print("\n💡 Diagnostic Results:")
        if len(threads) == 0:
            print("❌ No checkpoints found - SQLite persistence not working")
        elif len(conv_threads) > 0:
            print("✅ ConversationId-based threads found - fix is partially working")
        elif len(contact_threads) > 0:
            print("⚠️ Only contact-based threads found - conversationId might not be provided by GHL")
        else:
            print("❓ Unexpected thread ID format - needs investigation")
        
    except Exception as e:
        print(f"❌ Database Error: {e}")
        print("The checkpoint database might not exist or be accessible")
        # Initialize variables in case of error
        conv_threads = []
        contact_threads = []
        threads = []
    
    print("\n📋 Next Steps:")
    print("1. If no threads found → Fix isn't working")
    print("2. If only contact-based threads → GHL not sending conversationId")
    print("3. If conv- threads exist → Fix is working, check specific conversation")

def check_specific_contact(contact_id: str):
    """Check all thread IDs used by a specific contact"""
    db_path = 'app/checkpoints.db'
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        return
        
    print(f"\n🔍 Checking threads for contact: {contact_id}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Find all threads that might belong to this contact
        cursor.execute("""
            SELECT DISTINCT thread_id, COUNT(*) as count
            FROM checkpoints 
            WHERE thread_id LIKE ? OR thread_id LIKE ?
            GROUP BY thread_id
        """, (f'%{contact_id}%', f'contact-{contact_id}'))
        
        threads = cursor.fetchall()
        
        if threads:
            print(f"Found {len(threads)} thread(s) for this contact:")
            for thread_id, count in threads:
                print(f"  - {thread_id} ({count} checkpoints)")
                
            if len(threads) > 1:
                print("⚠️ Multiple thread IDs found - inconsistency detected!")
            else:
                print("✅ Single thread ID - consistency maintained")
        else:
            print("No threads found for this contact")
            
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    diagnose_thread_persistence()
    
    # Optional: check specific contact
    import sys
    if len(sys.argv) > 1:
        check_specific_contact(sys.argv[1])
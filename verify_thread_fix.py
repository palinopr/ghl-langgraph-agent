#!/usr/bin/env python3
"""
Verify thread ID mapping is working correctly in production
"""
import sqlite3
import os
from datetime import datetime
import re

def verify_thread_mapping():
    """Verify thread IDs are mapped correctly"""
    
    print("🔍 Verifying Thread ID Mapping Fix\n")
    
    db_path = 'app/checkpoints.db'
    
    # Check if database exists
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        print("Cannot verify - no checkpoints database exists")
        return
    
    print(f"✅ Database found at {db_path}")
    print(f"   Size: {os.path.getsize(db_path):,} bytes\n")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all threads
        cursor.execute("""
            SELECT DISTINCT thread_id, COUNT(*) as checkpoint_count
            FROM checkpoints 
            GROUP BY thread_id
            ORDER BY checkpoint_count DESC
        """)
        
        all_threads = cursor.fetchall()
        
        # Categorize threads
        uuid_pattern = re.compile(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$')
        contact_threads = []
        conv_threads = []
        uuid_threads = []
        other_threads = []
        
        for thread_id, count in all_threads:
            if thread_id.startswith('contact-'):
                contact_threads.append((thread_id, count))
            elif thread_id.startswith('conv-'):
                conv_threads.append((thread_id, count))
            elif uuid_pattern.match(thread_id):
                uuid_threads.append((thread_id, count))
            else:
                other_threads.append((thread_id, count))
        
        # Display results
        print("📊 Thread ID Analysis:")
        print(f"   Total threads: {len(all_threads)}")
        print(f"   ✅ Contact-based: {len(contact_threads)}")
        print(f"   ✅ Conversation-based: {len(conv_threads)}")
        print(f"   ❌ UUID threads: {len(uuid_threads)}")
        print(f"   ❓ Other format: {len(other_threads)}")
        print()
        
        # Show examples
        if contact_threads:
            print("✅ Contact-based threads (Good!):")
            for thread, count in contact_threads[:3]:
                print(f"   - {thread}: {count} checkpoints")
        
        if conv_threads:
            print("\n✅ Conversation-based threads (Good!):")
            for thread, count in conv_threads[:3]:
                print(f"   - {thread}: {count} checkpoints")
        
        if uuid_threads:
            print("\n❌ UUID threads (BAD - Fix not working!):")
            for thread, count in uuid_threads[:3]:
                print(f"   - {thread}: {count} checkpoints")
        
        # Get latest checkpoint timestamp
        cursor.execute("""
            SELECT checkpoint_id, thread_id
            FROM checkpoints 
            ORDER BY checkpoint_id DESC 
            LIMIT 5
        """)
        
        recent = cursor.fetchall()
        if recent:
            print("\n📅 Recent Checkpoints:")
            for checkpoint_id, thread_id in recent:
                # Extract timestamp from checkpoint_id if possible
                thread_type = "✅ Good" if not uuid_pattern.match(thread_id) else "❌ UUID"
                print(f"   {thread_type}: {thread_id[:40]}... ({checkpoint_id[:20]}...)")
        
        # Summary
        print("\n" + "="*60)
        if len(uuid_threads) == 0:
            print("🎉 SUCCESS: Thread ID mapping is working perfectly!")
            print("All threads follow the contact-{id} or conv-{id} pattern.")
        elif len(uuid_threads) < len(contact_threads + conv_threads):
            print("⚠️  PARTIAL SUCCESS: Some threads are mapped correctly.")
            print("Check if the fix was deployed recently.")
        else:
            print("❌ FAILURE: Thread ID mapping is NOT working!")
            print("Most threads are still using UUID format.")
            print("Verify the thread_mapper node is deployed and running.")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error analyzing database: {e}")

def check_recent_activity():
    """Check for recent checkpoint activity"""
    print("\n" + "="*60)
    print("🕐 Checking Recent Activity\n")
    
    try:
        conn = sqlite3.connect('app/checkpoints.db')
        cursor = conn.cursor()
        
        # Count checkpoints by hour
        cursor.execute("""
            SELECT 
                substr(checkpoint_id, 1, 13) as hour,
                COUNT(*) as count,
                COUNT(DISTINCT thread_id) as unique_threads
            FROM checkpoints 
            WHERE checkpoint_id > datetime('now', '-24 hours')
            GROUP BY hour
            ORDER BY hour DESC
            LIMIT 10
        """)
        
        hourly = cursor.fetchall()
        if hourly:
            print("Checkpoints in last 24 hours:")
            for hour, count, threads in hourly:
                print(f"   {hour}: {count} checkpoints, {threads} unique threads")
        else:
            print("No checkpoint activity in last 24 hours")
        
        conn.close()
        
    except:
        pass

if __name__ == "__main__":
    verify_thread_mapping()
    check_recent_activity()
    
    print("\n💡 Next Steps:")
    print("1. If UUID threads exist, check deployment status")
    print("2. Monitor new conversations for proper thread_ids")
    print("3. Run: python monitor_checkpoints.py watch")
    print("4. Test with real messages to verify persistence")
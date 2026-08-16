"""
mitchell.core.team_reminders
============================
Injected system reminders for Mitchell when team members are active.
"""

TEAM_COORDINATION_REMINDER = """
System Reminder: Team Coordination
You currently have active teammates working on sub-tasks.
Track their status, do not lose the thread of what you have delegated,
and wait for their completion reports via the hive event log before declaring 
a task finished.
"""

TEAM_SHUTDOWN_REMINDER = """
System Reminder: Team Shutdown
You are ending a session with active teammates. 
Ensure you dismiss them gracefully using `team_dismiss` so work is not 
silently abandoned.
"""

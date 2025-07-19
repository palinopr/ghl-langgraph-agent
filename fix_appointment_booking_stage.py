#!/usr/bin/env python3
"""
Fix for conversation enforcer to properly handle appointment booking stage
"""

# The issue: When customer selects a time (e.g. "10:00 AM"), the enforcer goes directly to
# CONFIRMING_APPOINTMENT stage instead of staying in WAITING_FOR_TIME_SELECTION where
# Sofia should use the appointment booking tool.

# Current logic (WRONG):
# - offered_times and not selected_time → WAITING_FOR_TIME_SELECTION
# - selected_time → CONFIRMING_APPOINTMENT

# Fixed logic (CORRECT):
# - offered_times and customer just selected time → WAITING_FOR_TIME_SELECTION (USE_APPOINTMENT_TOOL)
# - appointment already booked → CONFIRMING_APPOINTMENT

# The fix needs to check if this is the FIRST message after offering times
# If yes, stay in WAITING_FOR_TIME_SELECTION stage
# Only move to CONFIRMING_APPOINTMENT if appointment was actually created

def get_fixed_stage_logic():
    """
    Returns the corrected stage determination logic
    """
    return """
    # Check if customer just selected a time (first response after offering)
    just_selected_time = False
    if offered_times and not appointment_booked:
        # Check if last AI message offered times and current human message might be a selection
        for i in range(len(messages) - 1, -1, -1):
            msg = messages[i]
            if msg.type == "ai" and any(phrase in msg.content.lower() for phrase in ["horarios disponibles", "times available", "¿cuál prefieres?", "which do you prefer?"]):
                # Found the offer, now check if next human message is time selection
                if i + 1 < len(messages) and messages[i + 1].type == "human":
                    current_msg = messages[i + 1].content.lower()
                    time_indicators = ["am", "pm", ":00", "primera", "segunda", "tercera", 
                                     "10:", "2:", "4:", "mañana", "tarde"]
                    if any(indicator in current_msg for indicator in time_indicators):
                        just_selected_time = True
                break
    
    # Determine current stage based on what we have
    if not asked_for_name:
        analysis["current_stage"] = ConversationStage.GREETING
        analysis["next_action"] = "SEND_GREETING"
    elif asked_for_name and not got_name:
        analysis["current_stage"] = ConversationStage.WAITING_FOR_NAME
        analysis["next_action"] = "PROCESS_NAME"
    elif got_name and not asked_for_business:
        analysis["current_stage"] = ConversationStage.WAITING_FOR_NAME
        analysis["next_action"] = "ASK_FOR_BUSINESS"
    elif asked_for_business and not got_business:
        analysis["current_stage"] = ConversationStage.WAITING_FOR_BUSINESS
        analysis["next_action"] = "PROCESS_BUSINESS"
    elif got_business and not asked_for_problem:
        analysis["current_stage"] = ConversationStage.WAITING_FOR_BUSINESS
        analysis["next_action"] = "ASK_FOR_PROBLEM"
    elif asked_for_problem and not got_problem:
        analysis["current_stage"] = ConversationStage.WAITING_FOR_PROBLEM
        analysis["next_action"] = "PROCESS_PROBLEM"
    elif got_problem and not asked_for_budget:
        analysis["current_stage"] = ConversationStage.WAITING_FOR_PROBLEM
        analysis["next_action"] = "ASK_FOR_BUDGET"
    elif asked_for_budget and not got_budget:
        analysis["current_stage"] = ConversationStage.WAITING_FOR_BUDGET
        analysis["next_action"] = "PROCESS_BUDGET"
    elif got_budget and not asked_for_email:
        analysis["current_stage"] = ConversationStage.WAITING_FOR_BUDGET
        analysis["next_action"] = "ASK_FOR_EMAIL"
    elif asked_for_email and not got_email:
        analysis["current_stage"] = ConversationStage.WAITING_FOR_EMAIL
        analysis["next_action"] = "PROCESS_EMAIL"
    elif got_email and not offered_times:
        analysis["current_stage"] = ConversationStage.OFFERING_TIMES
        analysis["next_action"] = "OFFER_APPOINTMENT_TIMES"
    elif offered_times and just_selected_time:
        # FIXED: Customer just selected a time - Sofia should use appointment tool
        analysis["current_stage"] = ConversationStage.WAITING_FOR_TIME_SELECTION
        analysis["next_action"] = "USE_APPOINTMENT_TOOL"
    elif appointment_booked:
        # Only go to confirming if appointment was actually booked
        analysis["current_stage"] = ConversationStage.CONFIRMING_APPOINTMENT
        analysis["next_action"] = "SEND_CONFIRMATION"
    """

if __name__ == "__main__":
    print("Fix for appointment booking stage detection")
    print("=" * 60)
    print(get_fixed_stage_logic())
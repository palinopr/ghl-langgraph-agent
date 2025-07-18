"""
GHL Score and Field Updater - Ensures scores and extracted data are saved back to GHL
Inspired by n8n workflow's update mechanism
"""
from typing import Dict, Any, Optional
from app.tools.ghl_client import ghl_client
from app.utils.simple_logger import get_logger
from datetime import datetime

logger = get_logger("ghl_updater")

# GHL Custom Field IDs (from n8n workflow)
FIELD_MAPPINGS = {
    "score": "wAPjuqxtfgKLCJqahjo1",
    "intent": "Q1n5kaciimUU6JN5PBD6", 
    "business_type": "HtoheVc48qvAfvRUKhfG",
    "urgency_level": "dXasgCZFgqd62psjw7nd",
    "goal": "r7jFiJBYHiEllsGn7jZC",
    "budget": "4Qe8P25JRLW0IcZc5iOs",
    "name": "TjB0I5iNfVwx3zyxZ9sW",
    "preferred_day": "D1aD9KUDNm5Lp4Kz8yAD",
    "preferred_time": "M70lUtadchW4f2pJGDJ5"
}


class GHLUpdater:
    """Updates GHL contact records with scores and extracted data"""
    
    def __init__(self):
        self.ghl_client = ghl_client
        self.field_mappings = FIELD_MAPPINGS
    
    async def update_contact_from_state(
        self, 
        state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update GHL contact with score and extracted data from state
        
        Args:
            state: Workflow state containing analysis results
            
        Returns:
            Update result with success status
        """
        contact_id = state.get("contact_id")
        if not contact_id:
            logger.error("No contact_id in state, cannot update GHL")
            return {"success": False, "error": "No contact_id"}
        
        # Prepare updates
        updates = self._prepare_updates(state)
        
        if not updates["customFields"]:
            logger.info("No updates to send to GHL")
            return {"success": True, "message": "No updates needed"}
        
        try:
            # Update contact in GHL
            result = await self.ghl_client.update_contact(contact_id, updates)
            
            # Add tags based on score
            tags_result = await self._update_tags(contact_id, state)
            
            logger.info(
                f"Updated GHL contact {contact_id}: "
                f"Score={state.get('lead_score')}, "
                f"Category={state.get('lead_category')}"
            )
            
            return {
                "success": True,
                "contact_id": contact_id,
                "updates": updates,
                "tags_added": tags_result.get("tags_added", []),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to update GHL contact: {e}")
            return {
                "success": False,
                "error": str(e),
                "contact_id": contact_id
            }
    
    def _prepare_updates(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare update payload for GHL"""
        custom_fields = []
        
        # Always update score
        lead_score = state.get("lead_score", 0)
        custom_fields.append({
            "id": self.field_mappings["score"],
            "value": str(lead_score)
        })
        
        # Update intent (from score category)
        lead_category = state.get("lead_category", "cold")
        intent_map = {
            "cold": "EXPLORANDO",
            "warm": "EVALUANDO", 
            "hot": "LISTO_COMPRAR"
        }
        custom_fields.append({
            "id": self.field_mappings["intent"],
            "value": intent_map.get(lead_category, "EXPLORANDO")
        })
        
        # Update extracted data fields
        extracted_data = state.get("extracted_data", {})
        
        # Business type
        if extracted_data.get("business_type"):
            custom_fields.append({
                "id": self.field_mappings["business_type"],
                "value": extracted_data["business_type"]
            })
        
        # Goal
        if extracted_data.get("goal"):
            custom_fields.append({
                "id": self.field_mappings["goal"],
                "value": extracted_data["goal"]
            })
        
        # Budget
        if extracted_data.get("budget"):
            custom_fields.append({
                "id": self.field_mappings["budget"],
                "value": str(extracted_data["budget"])
            })
        
        # Name (verified name)
        if extracted_data.get("name"):
            custom_fields.append({
                "id": self.field_mappings["name"],
                "value": extracted_data["name"]
            })
        
        # Preferred day/time
        if extracted_data.get("preferred_day"):
            custom_fields.append({
                "id": self.field_mappings["preferred_day"],
                "value": extracted_data["preferred_day"]
            })
            
        if extracted_data.get("preferred_time"):
            custom_fields.append({
                "id": self.field_mappings["preferred_time"],
                "value": extracted_data["preferred_time"]
            })
        
        # Set urgency based on score
        urgency = "ALTA" if lead_score >= 8 else "NO_EXPRESADO"
        custom_fields.append({
            "id": self.field_mappings["urgency_level"],
            "value": urgency
        })
        
        # Prepare update object
        updates = {
            "customFields": custom_fields
        }
        
        # Update email if extracted
        if extracted_data.get("email"):
            updates["email"] = extracted_data["email"]
        
        # Update first name if extracted
        if extracted_data.get("name") and not state.get("contact_info", {}).get("firstName"):
            updates["firstName"] = extracted_data["name"]
        
        return updates
    
    async def _update_tags(self, contact_id: str, state: Dict[str, Any]) -> Dict[str, Any]:
        """Update contact tags based on score and category"""
        tags_to_add = []
        
        lead_score = state.get("lead_score", 0)
        lead_category = state.get("lead_category", "cold")
        
        # Category tags
        tags_to_add.append(f"lead-{lead_category}")
        
        # Score range tags
        if lead_score >= 8:
            tags_to_add.append("hot-lead")
            tags_to_add.append("ready-to-buy")
        elif lead_score >= 5:
            tags_to_add.append("warm-lead")
            tags_to_add.append("qualified")
        else:
            tags_to_add.append("cold-lead")
            tags_to_add.append("needs-nurturing")
        
        # Budget tags
        if state.get("extracted_data", {}).get("budget"):
            tags_to_add.append("has-budget")
            budget_str = str(state["extracted_data"]["budget"])
            if "300" in budget_str or int(re.sub(r'\D', '', budget_str) or 0) >= 300:
                tags_to_add.append("budget-300+")
        
        # Business type tags
        if state.get("extracted_data", {}).get("business_type"):
            business = state["extracted_data"]["business_type"].lower()
            tags_to_add.append(f"business-{business}")
        
        try:
            # Add tags to contact
            result = await self.ghl_client.add_tags(contact_id, tags_to_add)
            logger.info(f"Added tags to contact {contact_id}: {tags_to_add}")
            return {"success": True, "tags_added": tags_to_add}
        except Exception as e:
            logger.error(f"Failed to add tags: {e}")
            return {"success": False, "error": str(e)}


# Create singleton instance
ghl_updater = GHLUpdater()


async def update_ghl_after_analysis(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update GHL contact after intelligence analysis
    This should be called after the intelligence node completes
    
    Args:
        state: Workflow state with analysis results
        
    Returns:
        Updated state with GHL update results
    """
    # Update GHL
    update_result = await ghl_updater.update_contact_from_state(state)
    
    # Add update results to state
    state["ghl_update_result"] = update_result
    state["ghl_updated_at"] = datetime.now().isoformat()
    
    # Log update
    if update_result["success"]:
        logger.info(
            f"Successfully updated GHL contact {state.get('contact_id')} "
            f"with score {state.get('lead_score')}"
        )
    else:
        logger.error(
            f"Failed to update GHL contact {state.get('contact_id')}: "
            f"{update_result.get('error')}"
        )
    
    return state


# Node for workflow integration
async def ghl_update_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """GHL update node for workflow - updates contact after analysis"""
    return await update_ghl_after_analysis(state)


__all__ = [
    "GHLUpdater",
    "ghl_updater",
    "update_ghl_after_analysis",
    "ghl_update_node",
    "FIELD_MAPPINGS"
]


import re  # Add this import at the top
import os
from groq import Groq
from flask import current_app
import logging
import traceback

class ChatManager:
    def __init__(self):
        self.model = None
        self._setup_done = False

    def setup(self):
        api_key = current_app.config.get("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY")
        
        if not api_key:
            logging.error("AskVera: GROQ_API_KEY missing.")
            return

        try:
            self.model = Groq(api_key=api_key)
            self._setup_done = True
            logging.info("AskVera: Groq AI initialized successfully.")
        except Exception as e:
            logging.error(f"AskVera init failed: {e}")

    def get_response(self, user_message, context, user_identity, user_role="guest"):
        if not current_app.config.get("ENABLE_ASKVERA", False):
            return {"error": "AskVera is disabled.", "fallback": True}

        if not self.model: 
            self.setup()
        
        if not self.model: 
            return {"error": "AI service unavailable (Init failed).", "fallback": True}

        try:
            # Build service information for context
            service_info = ""
            if 'recent_services' in context and context['recent_services']:
                service_info += "\n\nRECENT SERVICES:\n"
                for idx, svc in enumerate(context['recent_services'][:5], 1):
                    service_info += f"{idx}. {svc['title']} - ₹{svc['price']} by {svc['provider']} ({svc['category']})\n"
            
            if 'high_rated_services' in context and context['high_rated_services']:
                service_info += "\n\nHIGH RATED SERVICES:\n"
                for idx, svc in enumerate(context['high_rated_services'][:5], 1):
                    rating_str = f"⭐{svc['rating']}" if svc['rating'] > 0 else "New"
                    service_info += f"{idx}. {svc['title']} - ₹{svc['price']} by {svc['provider']} ({rating_str})\n"
            
            if 'total_services' in context:
                service_info += f"\n\nTOTAL AVAILABLE SERVICES: {context['total_services']}"
            
            system_prompt = (
                f"You are AskVera, the official intelligent assistant of the SkillVerse platform. "
                f"Role: {user_role}. "
                f"Tone: Professional, Honest, Simple. "
                f"Context: {context.get('page', 'unknown')}. "
                f"{service_info}"
                f"\n\nAVAILABLE FEATURES: "
                f"1. User Management: Registration, Login, Profile (Client/Provider/Admin roles) "
                f"2. Services: Browse, Create, Edit, Approve/Reject (Admin), Categories "
                f"3. Orders: Place orders, Accept/Reject with reason (mandatory), Complete, Track status "
                f"4. Wallet System: Add money (Client/Provider only), View balance, Transactions (Credit/Debit), Platform fee (10%) "
                f"5. Bookings: Schedule availability slots, Book sessions, Approve/Reject bookings "
                f"6. Certificates: Auto-generated on order completion, Download PDF, Verify certificates "
                f"7. Chat: Real-time messaging between buyer and seller "
                f"8. Notifications: Order updates, Booking confirmations, Payment alerts "
                f"9. Reviews & Ratings: Rate services after completion "
                f"10. Admin Dashboard: Manage users, services, orders, view platform statistics "
                f"PAYMENT FLOW: Buyer pays → 90% to seller wallet + 10% platform fee to admin → Refund on rejection "
                f"ADMIN RESTRICTIONS: Cannot add money to wallet (only receives platform fees), Cannot place orders "
                f"RULES: "
                f"1. When asked about 'recent services', 'new services', or 'latest services', recommend from RECENT SERVICES list above. "
                f"2. When asked about 'best services', 'top rated', or 'high rated services', recommend from HIGH RATED SERVICES list above. "
                f"3. When asked about 'what services are available', mention total count and suggest browsing categories. "
                f"4. ONLY suggest/discuss existing features listed above. Do NOT invent features. "
                f"5. If data is not provided, say 'Data not available yet'. If count is zero, say 'No records found yet'. "
                f"6. Do NOT repeat visible dashboard numbers. Explain HOW to find/use features instead. "
                f"7. Be helpful but strictly realistic about the platform capabilities. "
                f"8. When asked about rejection, mention that rejection reason is MANDATORY."
            )
            
            response = self.model.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.3,
                max_tokens=300,
                top_p=0.9
            )
            
            ai_text = response.choices[0].message.content.strip()
            return {"response": ai_text, "suggestions": self.get_initial_suggestions(user_role)[:3]}
                
        except Exception as e:
            print(f"ChatManager Error: {e}")
            traceback.print_exc()
            return {"error": "I'm having trouble connecting right now.", "fallback": True}

    def get_initial_suggestions(self, role):
        if role == 'admin':
            return [
                "How can I manage users and services?",
                "How do I approve or reject services?",
                "How does the platform fee system work?",
                "How can I view all orders and transactions?",
                "What are my admin wallet restrictions?"
            ]
        elif role == 'guest':  # For non-logged-in users on home page
            return [
                "What is SkillVerse and how does it work?",
                "How do I sign up and get started?",
                "What are the benefits of joining SkillVerse?",
                "Can I both buy and sell services here?",
                "Is it safe to make payments on this platform?"
            ]
        elif role == 'provider':  # For service sellers
            return [
                "How do I create and list my services?",
                "How do I accept or reject orders?",
                "When and how do I receive payments?",
                "How can I manage my availability and bookings?",
                "How do I issue certificates to clients?"
            ]
        else: # Client (buyer)
            return [
                "What are the recent or new services available?",
                "Which services have the highest ratings?",
                "How do I find and book a service?",
                "How does the wallet and payment system work?",
                "How can I track my order status and get certificates?"
            ]

chat_manager = ChatManager()

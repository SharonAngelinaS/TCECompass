import os
import google.generativeai as genai
from openai import OpenAI
import json
import pandas as pd
from typing import Optional, Dict, List, Any
from dotenv import load_dotenv

# Load .env file if it exists (useful for local testing)
load_dotenv()

class LLMService:
    def __init__(self, data_processor):
        self.data_processor = data_processor
        # Initialize providers
        self.openai_client = None
        self.gemini_model = None
        
        # Check for OpenAI Key
        openai_key = os.getenv('OPENAI_API_KEY', '')
        if openai_key:
            try:
                self.openai_client = OpenAI(api_key=openai_key)
                print(f"Chatbot: OpenAI API initialized (Key ends in ...{openai_key[-4:]})")
            except Exception as e:
                print(f"Chatbot: Failed to initialize OpenAI: {e}")
            
        # Check for Gemini Key (used in Render)
        gemini_key = os.getenv('GEMINI_API_KEY', '')
        if gemini_key:
            try:
                genai.configure(api_key=gemini_key)
                self.gemini_model = genai.GenerativeModel('gemini-pro')
                print(f"Chatbot: Gemini API initialized (Key ends in ...{gemini_key[-4:]})")
            except Exception as e:
                print(f"Chatbot: Failed to initialize Gemini: {e}")
            
        if not self.openai_client and not self.gemini_model:
            available_vars = [k for k in os.environ.keys() if 'API' in k or 'KEY' in k]
            print(f"Warning: No AI API keys set. Available env vars: {available_vars}")
            print("To fix: Set GEMINI_API_KEY or OPENAI_API_KEY in Render Dashboard.")

    def generate_response(self, user_query: str, context_data: dict) -> str:
        """Generate response using available LLM with context from datasets"""
        user_query_lower = user_query.lower().strip()
        
        # Expanded greetings and fuzzy detection
        greetings = ['hi', 'hello', 'hey', 'ji', 'hllo', 'hey there', 'good morning', 'good afternoon', 'good evening']
        if any(user_query_lower == g or user_query_lower.startswith(g + ' ') for g in greetings) or len(user_query_lower) < 3:
            return "Hello! I'm TCE Compass, your AI-driven campus navigator. 🧭\n\nI can help you find classrooms, labs, or staff members. Try asking:\n" \
                   "• \"Where is Agile Lab?\"\n" \
                   "• \"Find Siva sir\"\n" \
                   "• \"Show me IG1 classroom\"\n\n" \
                   "How can I help you today?"
        
        context = context_data.get('context', '')
        results = context_data.get('results', [])
        needs_clarification = context_data.get('needs_clarification', False)
        is_person_query = context_data.get('is_person_query', False)
        
        # Basic filtering logic
        if results:
            # If multiple matching results, the LLM will handle them. 
            # If no LLM, we use fallback.
            pass

        # AI Generation
        if self.gemini_model or self.openai_client:
            system_prompt = "You are TCE Compass, a helpful campus navigator for Thiagarajar College of Engineering. " \
                            "Use the provided context to answer the user query professionally. " \
                            "If the context is empty, politely say you don't have that information in the database."
            user_message = f"User Query: {user_query}\n\nContext:\n{context}"
            
            try:
                if self.gemini_model:
                    response = self.gemini_model.generate_content(f"{system_prompt}\n\n{user_message}")
                    return response.text.strip()
                elif self.openai_client:
                    response = self.openai_client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}]
                    )
                    return response.choices[0].message.content.strip()
            except Exception as e:
                print(f"AI Error during generation: {e}")

        # Fallback for when AI is disabled or fails
        return self._generate_fallback_response(user_query, context_data)

    def _generate_clarification_response(self, user_query: str, results: list) -> str:
        depts = list(set(r.get('department', 'Unknown') for r in results))
        return f"I found multiple matches in different departments: {', '.join(depts)}. Please specify the department (e.g., 'from IT department')."

    def _generate_formal_response(self, user_query: str, results: list) -> str:
        if not results:
            return "I couldn't find that specific location in the campus database. 😅\n\nPlease try checking the name (e.g., 'Agile Lab' or 'IG1') or ask me to find a faculty member."
        
        # Format the first match nicely
        res = results[0]
        name = res.get('name', 'The location')
        floor = res.get('floor', 'Ground Floor')
        block = res.get('block', 'Main Block')
        dept = res.get('department', 'General')
        
        response = f"{name} is located in the {floor} of {block}, which belongs to the {dept} department."
        
        if res.get('faculty') and res.get('faculty') != 'N/A':
            response += f" It is handled by {res['faculty']}."
            
        return response

    def _generate_fallback_response(self, user_query: str, context_data: dict) -> str:
        results = context_data.get('results', [])
        if not results:
             return self._generate_formal_response(user_query, [])
        return self._generate_formal_response(user_query, results)

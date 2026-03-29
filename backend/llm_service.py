import os
import google.generativeai as genai
from openai import OpenAI
import json
import pandas as pd
from typing import Optional, Dict, List, Any

class LLMService:
    def __init__(self, data_processor):
        self.data_processor = data_processor
        # Initialize providers
        self.openai_client = None
        self.gemini_model = None
        # self.client is kept for backward compatibility with existing method calls
        self.client = None
        
        # Check for OpenAI Key
        openai_key = os.getenv('OPENAI_API_KEY', '')
        if openai_key:
            self.openai_client = OpenAI(api_key=openai_key)
            self.client = self.openai_client
            print("Chatbot: OpenAI API initialized.")
            
        # Check for Gemini Key (used in Render)
        gemini_key = os.getenv('GEMINI_API_KEY', '')
        if gemini_key:
            genai.configure(api_key=gemini_key)
            self.gemini_model = genai.GenerativeModel('gemini-pro')
            print("Chatbot: Gemini API initialized.")
            
        if not self.openai_client and not self.gemini_model:
            print("Warning: No AI API keys set. Using fallback response generation.")

    def generate_response(self, user_query: str, context_data: dict) -> str:
        """Generate response using available LLM with context from datasets"""
        user_query_lower = user_query.lower().strip()
        
        # Handle greetings and general queries
        greetings = ['hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening', 'greetings', 'hi there']
        if any(user_query_lower == g or user_query_lower.startswith(g + ' ') for g in greetings):
            return "Hello! I'm TCE Compass, your AI-driven campus navigator. I can help you find:\n\n" \
                   "• Classrooms\n• Labs\n• Staffrooms\n• Faculty members\n\n" \
                   "Try asking me questions like:\n" \
                   "- Where is Agile Lab?\n" \
                   "- Show me the location of IG1 classroom\n" \
                   "- Where is Subhashni mam?\n" \
                   "- Find Siva sir\n\n" \
                   "How can I help you today?"
        
        context = context_data.get('context', '')
        results = context_data.get('results', [])
        needs_clarification = context_data.get('needs_clarification', False)
        is_person_query = context_data.get('is_person_query', False)
        
        # Check if query specifies a department
        dept_keywords = {
            'csbs': 'Computer Science and Business Systems',
            'it': 'Information Technology',
            'amcs': 'Applied Mathematics and Computational Science'
        }
        specified_dept = next((dept for key, dept in dept_keywords.items() if key in user_query_lower), None)
        
        if specified_dept and results:
             results = [r for r in results if r.get('department', '').lower() == specified_dept.lower()]
             context_data['results'] = results

        # Clarification logic
        if is_person_query and len(results) > 1 and needs_clarification:
            return self._generate_clarification_response(user_query, results)

        # AI Generation
        if self.gemini_model or self.openai_client:
            system_prompt = "You are TCE Compass, a campus navigator for Thiagarajar College of Engineering. Use the provided context to answer professionally."
            user_message = f"Query: {user_query}\n\nContext:\n{context}"
            
            try:
                if self.gemini_model:
                    response = self.gemini_model.generate_content(f"{system_prompt}\n\n{user_message}")
                    return response.text.strip()
                else:
                    response = self.openai_client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}]
                    )
                    return response.choices[0].message.content.strip()
            except Exception as e:
                print(f"AI Error: {e}")

        # Fallback
        return self._generate_fallback_response(user_query, context_data)

    def _generate_clarification_response(self, user_query: str, results: list) -> str:
        depts = list(set(r.get('department', 'Unknown') for r in results))
        return f"I found multiple matches in different departments: {', '.join(depts)}. Which one are you looking for?"

    def _generate_formal_response(self, user_query: str, results: list) -> str:
        if not results:
            return "I couldn't find that location. Please check the name."
        res = results[0]
        return f"{res['name']} is located in {res['floor']} of {res['block']}, {res['department']} department."

    def _generate_fallback_response(self, user_query: str, context_data: dict) -> str:
        return self._generate_formal_response(user_query, context_data.get('results', []))

import os
import requests
import json
from datetime import datetime
from dotenv import load_dotenv
import time

load_dotenv()

HEYREACH_API_KEY = os.getenv('HEYREACH_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
LINKEDIN_ACCOUNT_ID = os.getenv('LINKEDIN_ACCOUNT_ID')

print("=" * 100)
print("🔄 BATCH NO THANKS PROCESSING - Advanced Rejection Handling")
print("=" * 100)


def load_leads_from_file(filename='leads.txt'):
    """Загружает список LinkedIn URLs из файла"""
    
    print(f"\n📥 Загрузка лидов из файла: {filename}")
    
    if not os.path.exists(filename):
        print(f"❌ Файл {filename} не найден!")
        print(f"   Создайте файл {filename} со списком LinkedIn URLs (по одному на строку)")
        return []
    
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    urls = []
    for line in lines:
        line = line.strip()
        
        if not line or line.startswith('#'):
            continue
        
        if not line.startswith('http'):
            line = f"https://www.linkedin.com/in/{line}/"
        
        line = line.rstrip('/')
        urls.append(line)
    
    print(f"✅ Загружено {len(urls)} лидов")
    
    return urls


def get_conversation_by_linkedin(linkedin_url):
    """Получает conversation конкретного лида"""
    
    print(f"\n   📥 Поиск диалога: {linkedin_url}")
    
    url = "https://api.heyreach.io/api/public/inbox/GetConversationsV2"
    
    headers = {
        "X-API-KEY": HEYREACH_API_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "filters": {
            "linkedInAccountIds": [LINKEDIN_ACCOUNT_ID],
            "leadProfileUrl": linkedin_url,
            "seen": None
        },
        "offset": 0,
        "limit": 1
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        if response.status_code != 200:
            print(f"      ❌ Ошибка API: {response.status_code}")
            return None
        
        data = response.json()
        conversations = data.get('items', [])
        
        if not conversations:
            print(f"      ⚠️ Диалог не найден")
            return None
        
        conversation = conversations[0]
        correspondent = conversation.get('correspondentProfile', {})
        lead_name = f"{correspondent.get('firstName', '')} {correspondent.get('lastName', '')}".strip()
        
        print(f"      ✅ Найден: {lead_name}")
        
        return conversation
        
    except requests.exceptions.RequestException as e:
        print(f"      ❌ Ошибка: {e}")
        return None


def create_full_no_thanks_analysis_prompt(conversation):
    """Создает ПОЛНЫЙ NO THANKS ANALYSIS промпт"""
    
    correspondent = conversation.get('correspondentProfile', {})
    
    lead_name = f"{correspondent.get('firstName', '')} {correspondent.get('lastName', '')}".strip()
    lead_company = correspondent.get('companyName', 'Unknown Company')
    lead_position = correspondent.get('position', 'Unknown Position')
    lead_location = correspondent.get('location', '')
    lead_linkedin = correspondent.get('profileUrl', '')
    lead_headline = correspondent.get('headline', '')
    
    messages = conversation.get('messages', [])
    conversation_history = []
    
    for msg in messages:
        sender = "You" if msg.get('sender') == 'ME' else lead_name
        created_at = msg.get('createdAt', '')
        body = msg.get('body', '[no text]')
        
        try:
            date_obj = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            date_str = date_obj.strftime('%Y-%m-%d %H:%M')
        except:
            date_str = created_at
        
        conversation_history.append(f"[{date_str}] {sender}: {body}")
    
    history_text = "\n".join(conversation_history) if conversation_history else "No message history"
    
    last_message = conversation.get('lastMessageText', '')
    last_message_at = conversation.get('lastMessageAt', '')
    total_messages = conversation.get('totalMessages', 0)
    today_date = datetime.now().strftime('%Y-%m-%d')
    
    # === ПОЛНЫЙ NO THANKS ANALYSIS PROMPT ===
    prompt = f"""You are an expert B2B sales researcher for Interexy, a premium software development company.

ABOUT INTEREXY:
- Company: American software development firm (Miami HQ)
- Services: Senior-level developers (top 2% of market), team augmentation, custom development
- Expertise: Healthcare, Fintech, Blockchain/Web3, AI/ML, Energy
- Team: 350+ senior engineers across US, Poland, Estonia, UAE
- Notable clients: RWE, E.ON (energy sector), healthcare & fintech companies
- Guarantee: 10-day engineer replacement, high-quality code standards

YOUR TASK:
Analyze this B2B lead using the RESEARCH FRAMEWORK below. Use web search extensively to gather current information. Focus on generating follow-up messages for leads who said "no thanks" or gave minimal responses. Return findings in structured JSON format.

=== LEAD INFORMATION ===
Name: {lead_name}
Company: {lead_company}
Position: {lead_position}
Location: {lead_location}
LinkedIn: {lead_linkedin}
Headline: {lead_headline}

=== CONVERSATION HISTORY ===
{history_text}

Last message: {last_message}
Date: {last_message_at}
Total messages: {total_messages}

=== RESEARCH FRAMEWORK ===

LEVEL 1: PERSONAL PROFILE ANALYSIS (LinkedIn + Web Search)

1.1 CURRENT ROLE ANALYSIS
Use web search to find:
✓ Position: exact title
✓ Time in role: months/years
✓ Department: sales/product/tech/ops/etc
✓ Reports to: who (CEO/CTO/etc)
✓ Team size: if mentioned (10 direct reports = manager level)
✓ Decision authority: decision maker / influencer / user

WHAT THIS GIVES YOU:
- New role (<6 months) → "congrats on new role" opener, usually open to new tools
- Long in role (2+ years) → expert, ask for insights
- Head of/Director → strategic questions
- VP/C-level → high-level business impact questions
- Wrong person → redirect to correct person

1.2 CAREER TRAJECTORY
Use web search to find:
✓ Previous companies: where they worked
✓ Industry switches: fintech → healthcare = interesting
✓ Role progression: engineer → manager → director
✓ Time at each role: job hopper vs. stable

WHAT THIS GIVES YOU:
- Industry switchers = ask "what's different between X and Y industry?"
- Rapid progression = ambitious, growth-focused
- Similar backgrounds = "I see you also worked at..."
- Career transition = opportunity for different angle

1.3 ACTIVITY & SIGNALS
Use web search to find:
✓ Recent posts: what they post about
✓ #HIRING badge: hiring = potential need
✓ #OPEN_TO_WORK: job seeking = different approach
✓ Event speaking: conferences = thought leader
✓ Recent certifications: learning mode
✓ Company changes: new job, promotion, company exit

WHAT THIS GIVES YOU:
- Hiring = "saw you're hiring for X, curious about..."
- Recent posts = conversation starter
- Speaking = "saw your talk at X conference"
- Job change = different conversation approach

LEVEL 2: COMPANY BASICS (LinkedIn Company Page + Web)

2.1 COMPANY BASICS
Use web search to find:
✓ Founded: year
✓ Size: employee count
✓ Locations: HQ + offices
✓ Industry: actual industry
✓ Stage: startup/growth/enterprise
✓ Company culture: tech-first / non-tech / hybrid

WHAT THIS GIVES YOU:
- Startup (<50 people, <3 years) → growth pain points, scaling questions
- Scaleup (50-500, 3-7 years) → platform optimization, team expansion
- Enterprise (500+, 7+ years) → modernization, legacy system questions

2.2 RECENT COMPANY ACTIVITY
Use web search to find:
✓ Recent posts: hiring/product launches/awards
✓ Job openings: which roles they're hiring
✓ Team growth: compare employee count vs 3 months ago
✓ New locations: expansion signals
✓ Org changes: restructuring, new executives

WHAT THIS GIVES YOU:
- 5+ open engineering roles = scaling tech team
- New office = expansion mode
- Awards/recognition = "congrats on X award" opener

LEVEL 3: DEEP RESEARCH (Web Search Required)

3.1 FUNDING & GROWTH
Search query: "{lead_company} funding round 2025 2026"
Find:
✓ Last funding: Series A/B/C, amount, date
✓ Total raised: $X million
✓ Investors: who backed them
✓ Valuation: if public
✓ Revenue: if mentioned in articles
✓ Growth trajectory: growing fast / stable / struggling

WHAT THIS GIVES YOU:
- Recent funding (<6 months) → "congrats on Series B! As you scale with new capital, what's the biggest tech challenge?"
- No recent funding + growing → bootstrapped, cost-conscious
- Big name investors → "saw a16z backed you, interesting"

3.2 PRODUCT & TECH STACK
Search queries:
- "{lead_company} product launch 2025 2026"
- "{lead_company} tech stack"
- "{lead_company} platform technology"

Find:
✓ Main product: what they sell
✓ Recent launches: new features/products
✓ Tech mentioned: React/Python/blockchain/AI
✓ Integrations: Stripe/Salesforce/etc
✓ Platform type: SaaS/marketplace/infrastructure
✓ Technical complexity: simple / medium / complex

WHAT THIS GIVES YOU:
- Recent launch = "saw you launched X, curious about adoption"
- Tech stack visible = technical questions
- Platform type = specific pain points (marketplace scaling, SaaS onboarding, etc)

3.3 NEWS & RECENT DEVELOPMENTS
Search query: "{lead_company} news 2025 2026"
Find:
✓ Partnerships announced: with who, when
✓ Acquisitions: bought/sold
✓ Product milestones: user count, revenue
✓ Industry awards: recognition
✓ Executive changes: new CEO/CTO
✓ Market expansion: new regions, verticals
✓ Controversies: if any - be careful

WHAT THIS GIVES YOU:
- Partnership announcement = "saw the Stripe partnership, curious how..."
- Acquisition = "congrats on acquiring X, integration challenges?"
- Milestones = "1M users is impressive, what's next?"

3.4 COMPETITIVE LANDSCAPE
Search query: "{lead_company} competitors alternatives"
Find:
✓ Direct competitors: who they compete with
✓ Market position: leader/challenger/niche
✓ Differentiation: what makes them unique
✓ Market trends: industry growing/declining
✓ Market pressure: competitive intensity

WHAT THIS GIVES YOU:
- "How do you differentiate from [competitor]?"
- "Market seems crowded - what's your moat?"
- Shows you understand their space

3.5 REGULATORY & INDUSTRY CONTEXT
Search queries based on industry:
- Fintech: "CSRD MiCA regulations EU 2026"
- Healthcare: "HIPAA compliance digital health 2025 2026"
- Circular economy: "EPR extended producer responsibility EU 2025 2026"
- Crypto: "MiCA stablecoin regulations 2025 2026"
- Energy: "{lead_company} industry renewable energy transition 2025 2026"

Find:
✓ Recent regulations: what changed
✓ Compliance requirements: new mandates
✓ Industry trends: what's hot
✓ Market drivers: what's pushing change
✓ Compliance deadlines: upcoming dates

WHAT THIS GIVES YOU:
- Timely, relevant questions
- Shows deep industry knowledge
- Opens compliance/tech discussion

LEVEL 4: PAIN POINT MAPPING

4.1 ROLE-SPECIFIC PAIN POINTS

Analyze based on position title:

HEAD OF DIGITAL/INNOVATION likely faces:
- Platform scaling challenges
- Legacy system integration
- Team capacity (build vs buy decisions)
- Innovation speed pressures
- Tech debt management
- Vendor evaluation and selection
- Budget allocation decisions

PRODUCT MANAGER likely faces:
- Feature velocity demands
- User feedback integration
- A/B testing infrastructure
- Technical feasibility assessments
- Cross-functional alignment issues
- Roadmap prioritization
- Engineering capacity constraints

CEO/FOUNDER likely faces:
- Capital efficiency concerns
- Time to market pressures
- Team scaling challenges
- Product-market fit validation
- Go-to-market strategy
- Fundraising priorities
- Board management

CTO/ENGINEERING LEAD likely faces:
- Technical debt accumulation
- Team productivity optimization
- Architecture decisions
- Hiring senior talent
- System reliability/uptime
- Technology stack decisions
- Engineering culture building

HEAD OF PRODUCT likely faces:
- Product-market fit validation
- Feature prioritization under constraints
- User research vs speed tradeoffs
- Cross-functional coordination
- Roadmap vs tech debt balance
- Competitive feature parity
- Resource allocation decisions

VP OPERATIONS likely faces:
- Process scaling challenges
- System integration complexity
- Efficiency optimization
- Team productivity metrics
- Tool consolidation
- Vendor management
- Cost optimization pressures

4.2 STAGE-SPECIFIC PAIN POINTS

EARLY STAGE STARTUP (<2 years, Seed):
- MVP development speed
- Finding product-market fit
- Limited engineering resources
- Capital efficiency
- Rapid iteration needs
- Founding team capacity
- Technical foundation decisions

GROWTH STAGE (Series A/B, 2-5 years):
- Scaling infrastructure
- Team expansion (10x growth)
- Platform stability
- Feature velocity vs tech debt
- Customer success scaling
- Process formalization
- Hiring senior talent challenges

SCALE-UP (Series C+, 5+ years):
- Legacy modernization
- Enterprise features
- Compliance/security requirements
- Geographic expansion
- M&A integration
- Platform reliability at scale
- Organizational complexity

ENTERPRISE (7+ years, established):
- Digital transformation
- Legacy system replacement
- Innovation vs stability tradeoff
- Vendor consolidation
- Regulatory compliance
- Cost optimization
- Modernization initiatives

4.3 VENDOR APPROACH INFERENCE

Analyze to infer current approach:

IN-HOUSE SIGNALS:
- Large engineering team (50+)
- Lots of engineering job openings
- Tech blog/engineering culture focus
- "We build everything" messaging
- Recent tech leadership hires

VENDOR-USING SIGNALS:
- Smaller tech team relative to scale
- No recent engineering hiring
- Partnership announcements
- Integration-focused product
- Lean operational model

HYBRID SIGNALS:
- Medium team (20-50)
- Selective hiring (senior only)
- Some partnerships, some builds
- "Best of both" approach mentions

BUILD VS BUY PHILOSOPHY:
- Build-first: Startups, tech companies, high IP value
- Buy-when-needed: Non-tech, fast-growth, capital-efficient
- Hybrid: Scale-ups balancing speed and control

4.4 TIMING TRIGGERS ANALYSIS

ACTIVE TRIGGERS (0-3 months):
- Recent funding announcement
- Product launch just happened
- Rapid hiring (5+ roles open)
- New executive hire
- Market expansion announced
- Acquisition just closed
- Technical incident/outage

UPCOMING TRIGGERS (3-6 months):
- Expected next funding round
- Seasonal scaling (e.g. Black Friday prep)
- Regulatory deadline approaching
- Competitor launch expected
- Contract renewals coming up
- Fiscal year planning cycle

POTENTIAL TRIGGERS (6-12 months):
- Long-term growth targets
- Geographic expansion plans
- New product line roadmap
- Maturity milestones
- Industry trend adoption

VENDOR EVALUATION PATTERNS:
- Annual budget cycle: Q4/Q1 evaluation
- Quarterly reviews: Every 3 months
- Triggered: When capacity hit, urgent need, project-based
- Ad-hoc: No clear pattern

=== OUTPUT FORMAT ===

Return ONLY valid JSON with this EXACT structure:

{{
  "lead_profile": {{
    "current_role": {{
      "title": "exact position",
      "time_in_role": "X months/years",
      "department": "sales/product/tech/ops",
      "reports_to": "CEO/CTO/etc or unknown",
      "team_size": "number or unknown",
      "decision_authority": "decision_maker/influencer/user/unknown",
      "insight": "what this tells us about their priorities"
    }},
    "career_trajectory": {{
      "previous_companies": ["Company 1", "Company 2"],
      "industry_switches": "any notable industry changes",
      "progression": "engineer->manager->director pattern",
      "insight": "what this tells us about their ambition/focus"
    }},
    "activity_signals": {{
      "hiring": true,
      "recent_posts_topics": ["topic1", "topic2"],
      "speaking_events": ["event1 if any"],
      "certifications": ["recent cert if any"],
      "company_changes": "new job/promotion/exit if any",
      "insight": "best conversation hooks from activity"
    }}
  }},
  
  "company_basics": {{
    "founded": "year",
    "size": "employee count",
    "locations": ["location1", "location2"],
    "industry": "actual industry",
    "stage": "startup/growth/enterprise",
    "company_culture": "tech-first/non-tech/hybrid",
    "stage_insight": "what pain points this stage typically has"
  }},
  
  "company_activity": {{
    "recent_hiring": {{
      "open_roles_count": 0,
      "key_roles": ["role1", "role2"],
      "insight": "what this hiring pattern suggests"
    }},
    "team_growth": "growing/stable/shrinking",
    "expansion": ["new office location if any"],
    "awards": ["recent award if any"],
    "org_changes": ["restructuring/new executives if any"]
  }},
  
  "deep_research": {{
    "funding": {{
      "last_round": "Series X, $Y million, date",
      "total_raised": "$X million",
      "investors": ["investor1", "investor2"],
      "growth_trajectory": "growing fast/stable/struggling",
      "funding_insight": "what recent funding means for outreach"
    }},
    "product": {{
      "main_product": "what they sell",
      "recent_launches": [
        {{
          "name": "feature/product name",
          "date": "YYYY-MM-DD",
          "description": "brief description"
        }}
      ],
      "tech_stack": ["React", "Python", "AWS"],
      "platform_type": "SaaS/marketplace/infrastructure",
      "technical_complexity": "simple/medium/complex",
      "product_insight": "technical conversation hooks"
    }},
    "news": [
      {{
        "date": "YYYY-MM-DD",
        "headline": "headline",
        "summary": "brief summary",
        "source": "source URL",
        "outreach_hook": "how to use this in conversation"
      }}
    ],
    "competitive_landscape": {{
      "competitors": ["competitor1", "competitor2"],
      "market_position": "leader/challenger/niche",
      "differentiation": "what makes them unique",
      "market_trend": "growing/stable/declining",
      "market_pressure": "high/medium/low competitive intensity"
    }},
    "regulatory_context": {{
      "recent_regulations": [
        {{
          "regulation": "regulation name",
          "impact": "how it affects company",
          "date": "when it takes effect"
        }}
      ],
      "compliance_requirements": ["requirement1"],
      "compliance_deadlines": ["deadline1 if any"],
      "industry_trend": "what's driving change in industry"
    }}
  }},
  
  "pain_point_analysis": {{
    "role_specific_pain_points": [
      "pain point 1 based on their role",
      "pain point 2",
      "pain point 3"
    ],
    "stage_specific_pain_points": [
      "pain point 1 based on company stage",
      "pain point 2",
      "pain point 3"
    ],
    "evidence_from_research": [
      "evidence 1 from news/hiring/etc that confirms pain point",
      "evidence 2"
    ]
  }},
  
  "vendor_approach_inference": {{
    "current_solution_hypothesis": "likely_in_house/likely_vendors/likely_hybrid",
    "confidence": "high/medium/low",
    "evidence": [
      "specific signal 1 (e.g. 50 engineers on team)",
      "specific signal 2 (e.g. no vendor partnerships visible)",
      "specific signal 3"
    ],
    "vendor_geography_preference": {{
      "hypothesis": "likely prefers US/EU/LatAm/Eastern Europe",
      "reasoning": "based on company location and industry patterns"
    }},
    "build_vs_buy_philosophy": {{
      "assessment": "build-first/buy-when-needed/hybrid-approach",
      "reasoning": "based on team size, stage, hiring patterns",
      "implications": "what this means for vendor pitch"
    }}
  }},
  
  "timing_triggers_analysis": {{
    "active_triggers": [
      {{
        "trigger": "specific event happening now",
        "timeframe": "0-3 months",
        "urgency": "high/medium/low",
        "how_it_creates_need": "explanation"
      }}
    ],
    "upcoming_triggers": [
      {{
        "trigger": "event likely in next 3-6 months",
        "timeframe": "3-6 months",
        "probability": "high/medium/low",
        "how_to_use": "how to position this in message"
      }}
    ],
    "potential_triggers": [
      {{
        "trigger": "future event 6-12 months",
        "timeframe": "6-12 months",
        "how_to_stay_on_radar": "nurture strategy"
      }}
    ],
    "vendor_evaluation_pattern": {{
      "likely_pattern": "triggered/quarterly/annual",
      "decision_maker": "who decides on vendors",
      "typical_timeline": "1-4 weeks / 4-8 weeks / 2-6 months",
      "criteria": ["what they care about when selecting"]
    }},
    "urgency_assessment": {{
      "urgency_level": "high/medium/low/none",
      "primary_driver": "what's creating urgency if any",
      "timing_recommendation": "reach out now / wait X weeks / wait for trigger"
    }}
  }},
  
  "conversation_analysis": {{
    "conversation_stage": "initial_response/engaged/qualification/negotiation/rejected",
    "messages_exchanged": 0,
    "lead_responsiveness": "high/medium/low",
    "interest_signals": ["signal1 from messages", "signal2"],
    "objections_raised": ["objection1 if any"],
    "questions_asked": ["question1 if any"],
    "rejection_analysis": {{
      "rejection_type": "hard_no/soft_no/wrong_person/bad_timing/not_applicable",
      "confidence": "high/medium/low",
      "evidence": "what in conversation suggests this type",
      "recommended_approach": "accept and move on / one more try / redirect / wait and nurture"
    }}
  }},
  
  "qualification": {{
    "status": "qualified/partially_qualified/not_qualified/too_early",
    "fit_score": 5,
    "reasoning": "why this qualification status",
    "budget_indicator": "high/medium/low/unknown",
    "authority_level": "decision_maker/influencer/user/unknown",
    "need_urgency": "high/medium/low/none_detected",
    "vendor_readiness": "ready/maybe_soon/not_ready/never"
  }},
  
  "no_thanks_response_strategy": {{
    "assumption_questions": [
      {{
        "message": "full message text with acknowledge + assumption + binary question",
        "type": "vendor_geography/build_vs_buy/capacity/technology",
        "reasoning": "why this assumption is relevant based on research",
        "expected_outcome": "what you hope to learn or achieve"
      }},
      {{
        "message": "second assumption question variant",
        "type": "type",
        "reasoning": "reasoning",
        "expected_outcome": "outcome"
      }}
    ],
    
    "clarification_messages": [
      {{
        "message": "full message text with acknowledge + news hook + pain connection + capability",
        "news_hook": "specific recent event/launch/funding",
        "pain_created": "specific challenge this creates",
        "interexy_capability": "exact capability we offer",
        "reasoning": "why this is relevant based on research"
      }},
      {{
        "message": "second clarification variant",
        "news_hook": "hook",
        "pain_created": "pain",
        "interexy_capability": "capability",
        "reasoning": "reasoning"
      }}
    ],
    
    "future_focused_questions": [
      {{
        "message": "full message text with acknowledge + timing question",
        "question_type": "evaluation_cycle/growth_trigger/capacity_trigger/budget_cycle",
        "reasoning": "why this timing question is relevant",
        "expected_insight": "what you hope to learn"
      }},
      {{
        "message": "second timing question variant",
        "question_type": "type",
        "reasoning": "reasoning",
        "expected_insight": "insight"
      }}
    ],
    
    "benchmark_offers": [
      {{
        "message": "full message text with acknowledge + specific benchmark offer",
        "metric": "specific KPI or benchmark",
        "relevance": "why this would be useful to them",
        "goal": "stay top-of-mind without being pushy"
      }}
    ],
    
    "alternative_angles": [
      {{
        "message": "full message text",
        "angle_type": "pivot_to_learning/pivot_to_referral/pivot_to_person/pivot_to_value",
        "reasoning": "why this different angle might work",
        "goal": "what you're trying to achieve"
      }},
      {{
        "message": "second alternative angle",
        "angle_type": "type",
        "reasoning": "reasoning",
        "goal": "goal"
      }}
    ],
    
    "recommended_best_message": {{
      "message_text": "the single best message to send based on all analysis",
      "message_type": "assumption/clarification/future_focused/benchmark/alternative",
      "why_this_one": "detailed reasoning for why this is best choice",
      "backup_option": "if first doesn't work, try this next"
    }}
  }},
  
  "recommended_action": {{
    "next_step": "specific action with timeframe",
    "should_follow_up": true,
    "follow_up_timing": "now/3 days/1 week/wait for trigger/don't follow up",
    "message_angle": "which message type to use from no_thanks_response_strategy",
    "personalization_hooks": [
      "hook 1 with context why it works",
      "hook 2 with context",
      "hook 3 with context"
    ],
    "timing": "when to reach out (now/wait X days/specific trigger)",
    "priority": "high/medium/low/skip",
    "if_ignored_next_step": "what to do if this message also gets no response"
  }},
  
  "interexy_value_props": {{
    "most_relevant": [
      "value prop 1 based on their pain points and vendor readiness",
      "value prop 2",
      "value prop 3"
    ],
    "case_studies_to_mention": [
      "RWE/E.ON energy sector work if relevant",
      "Other relevant case study"
    ],
    "technical_expertise_highlight": "which tech expertise to emphasize based on their stack/needs",
    "differentiation_angle": "how to position Interexy vs likely current solution"
  }},
  
  "executive_summary": "2-3 sentence summary of: rejection type, lead quality, whether to follow up, and best approach if following up"
}}

IMPORTANT INSTRUCTIONS:
1. Use web search extensively - search for company news, funding, product launches, regulatory context, hiring patterns
2. Find REAL information with REAL sources and dates - don't invent
3. If information not found, say "not found" - don't make up data
4. Focus on RECENT information (last 12 months prioritized)
5. Provide SPECIFIC, ACTIONABLE insights - not generic
6. Match pain points to REAL evidence from research
7. Generate COMPLETE message texts in "no_thanks_response_strategy" - ready to send
8. Base all assumptions and questions on ACTUAL research findings
9. Be honest about rejection type - if it's hard no, say so
10. Return ONLY valid JSON, no markdown blocks, no extra text
11. Today's date for reference: {today_date}"""
    
    return prompt, lead_name, lead_company


def analyze_with_openai(prompt, lead_name):
    """Анализирует через OpenAI с web search"""
    
    print(f"      🤖 DEEP ANALYSIS через OpenAI (с web search)...")
    
    url = "https://api.openai.com/v1/responses"
    
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "gpt-4o",
        "tools": [{"type": "web_search"}],
        "input": prompt
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=240)
        
        if response.status_code != 200:
            print(f"      ❌ OpenAI error: {response.status_code}")
            return None
        
        data = response.json()
        
        # Извлекаем текст
        output_array = data.get('output', [])
        output_text = ""
        
        for item in output_array:
            if item.get('type') == 'message':
                content_array = item.get('content', [])
                for content_item in content_array:
                    if content_item.get('type') == 'output_text':
                        output_text = content_item.get('text', '')
                        break
                if output_text:
                    break
        
        if not output_text:
            print(f"      ❌ No output_text")
            return None
        
        # Парсим JSON
        output_text = output_text.replace('```json', '').replace('```', '').strip()
        json_start = output_text.find('{')
        json_end = output_text.rfind('}') + 1
        
        if json_start != -1 and json_end > json_start:
            output_text = output_text[json_start:json_end]
        
        analysis = json.loads(output_text)
        print(f"      ✅ Analysis готов (rejection: {analysis.get('conversation_analysis', {}).get('rejection_analysis', {}).get('rejection_type', 'N/A')})")
        return analysis
        
    except json.JSONDecodeError as e:
        print(f"      ❌ JSON parse error: {e}")
        return None
    except Exception as e:
        print(f"      ❌ Error: {e}")
        return None


def create_no_thanks_message_generation_prompt(analysis, metadata):
    """Создает ПОЛНЫЙ промпт для генерации NO THANKS сообщений"""
    
    lead_name = metadata.get('lead_name', 'Unknown')
    lead_company = metadata.get('lead_company', 'Unknown')
    lead_position = metadata.get('lead_position', 'Unknown')
    first_name = lead_name.split()[0] if lead_name else 'there'
    
    qual = analysis.get('qualification', {})
    company = analysis.get('company_basics', {})
    pain_points = analysis.get('pain_point_analysis', {})
    deep_research = analysis.get('deep_research', {})
    vendor_approach = analysis.get('vendor_approach_inference', {})
    timing_triggers = analysis.get('timing_triggers_analysis', {})
    conversation = analysis.get('conversation_analysis', {})
    rejection = conversation.get('rejection_analysis', {})
    no_thanks_strategy = analysis.get('no_thanks_response_strategy', {})
    value_props = analysis.get('interexy_value_props', {})
    
    # Проверяем длину - если промпт слишком большой, сократим некоторые секции
    prompt_length_estimate = len(str(analysis))
    
    # Если analysis очень большой (>20000 символов), берем только ключевые части
    if prompt_length_estimate > 20000:
        print(f"      ⚠️ Large analysis ({prompt_length_estimate} chars), using condensed version")
        news_snippet = json.dumps(deep_research.get('news', [])[:1], indent=2)
        funding_snippet = json.dumps(deep_research.get('funding', {}), indent=2)
    else:
        news_snippet = json.dumps(deep_research.get('news', [])[:2], indent=2)
        funding_snippet = json.dumps(deep_research.get('funding', {}), indent=2)
    
    prompt = f"""You are an expert B2B sales copywriter specializing in handling rejections and re-engaging cold leads.

CONTEXT:
This lead said "no thanks" or gave minimal response. Your task is to generate follow-up messages that acknowledge the rejection gracefully while finding alternative angles to continue the conversation or stay top-of-mind.

=== LEAD INFORMATION ===
Name: {lead_name}
Company: {lead_company}
Position: {lead_position}

=== ANALYSIS SUMMARY ===

QUALIFICATION:
Status: {qual.get('status', 'N/A')}
Fit Score: {qual.get('fit_score', 0)}/10
Vendor Readiness: {qual.get('vendor_readiness', 'unknown')}
Reasoning: {qual.get('reasoning', 'N/A')}

COMPANY CONTEXT:
Stage: {company.get('stage', 'N/A')}
Size: {company.get('size', 'N/A')} employees
Industry: {company.get('industry', 'N/A')}

REJECTION ANALYSIS:
Type: {rejection.get('rejection_type', 'unknown')}
Confidence: {rejection.get('confidence', 'medium')}
Evidence: {rejection.get('evidence', 'N/A')}
Recommended Approach: {rejection.get('recommended_approach', 'N/A')}

PAIN POINTS IDENTIFIED:
Role-Specific:
{chr(10).join(f"- {p}" for p in pain_points.get('role_specific_pain_points', [])[:3])}

Stage-Specific:
{chr(10).join(f"- {p}" for p in pain_points.get('stage_specific_pain_points', [])[:3])}

Evidence from Research:
{chr(10).join(f"- {e}" for e in pain_points.get('evidence_from_research', [])[:3])}

VENDOR APPROACH HYPOTHESIS:
Current Solution: {vendor_approach.get('current_solution_hypothesis', 'unknown')}
Evidence:
{chr(10).join(f"- {e}" for e in vendor_approach.get('evidence', [])[:3])}

Build vs Buy Philosophy: {vendor_approach.get('build_vs_buy_philosophy', {}).get('assessment', 'unknown')}
Implications: {vendor_approach.get('build_vs_buy_philosophy', {}).get('implications', 'N/A')}

TIMING TRIGGERS:
Active Triggers (0-3 months):
{json.dumps(timing_triggers.get('active_triggers', [])[:2], indent=2)}

Upcoming Triggers (3-6 months):
{json.dumps(timing_triggers.get('upcoming_triggers', [])[:2], indent=2)}

Vendor Evaluation Pattern:
Pattern: {timing_triggers.get('vendor_evaluation_pattern', {}).get('likely_pattern', 'unknown')}
Timeline: {timing_triggers.get('vendor_evaluation_pattern', {}).get('typical_timeline', 'unknown')}

Urgency Assessment:
Level: {timing_triggers.get('urgency_assessment', {}).get('urgency_level', 'unknown')}
Driver: {timing_triggers.get('urgency_assessment', {}).get('primary_driver', 'N/A')}
Timing Recommendation: {timing_triggers.get('urgency_assessment', {}).get('timing_recommendation', 'N/A')}

RECENT NEWS/HOOKS:
{news_snippet}

FUNDING INFO:
{funding_snippet}

INTEREXY VALUE PROPS TO EMPHASIZE:
{chr(10).join(f"- {vp}" for vp in value_props.get('most_relevant', [])[:3])}

Differentiation Angle: {value_props.get('differentiation_angle', 'N/A')}

---

YOUR TASK:
Generate 12-15 follow-up message variants specifically designed for "no thanks" handling.

=== MESSAGE TYPES TO GENERATE ===

1. ASSUMPTION QUESTIONS (3-4 variants)
Pattern: Acknowledge + Make educated guess + Binary question

Examples based on research:
- "Fair enough, {first_name}! I'm guessing you already work with [vendors from X region] - am I right?"
- "Understood, {first_name}! I assume you have an in-house team handling [specific area]?"
- "No worries, {first_name}! Sounds like you've already solved [X] through [likely approach]?"
- "Got it, {first_name}! I imagine with [team size], you prefer to [build/buy] for [specific need]?"

Requirements:
- Base assumption on REAL evidence from vendor_approach_inference
- Keep it conversational and non-pushy
- Binary question at the end
- Show you did research

2. CLARIFICATION - WHY I REACHED OUT (2-3 variants)
Pattern: Acknowledge + Specific reason (news hook) + Pain it creates + Our capability + Collaboration possibility

Template:
"Fair enough, {first_name}! The reason I reached out is I saw [specific recent event from news].
Typically when companies [do X], they face [specific challenge].
We specialize in [exact capability], thought there might be room for collaboration.
But no worries if timing isn't right!"

Requirements:
- Use REAL news from deep_research.news
- Connect news to specific pain point from analysis
- Mention specific Interexy capability
- Stay humble ("thought there might be...")

3. FUTURE-FOCUSED / TIMING QUESTIONS (3-4 variants)
Pattern: Acknowledge + Timing-related question based on triggers

Examples based on timing_triggers_analysis:
- "Understood, {first_name}! What would typically trigger {lead_company} to evaluate [vendors/solutions]?"
- "No problem, {first_name}! When you do scale to [next milestone], what becomes the biggest bottleneck?"
- "Got it, {first_name}! If internal capacity becomes constrained, would you consider external help or just hire more?"
- "Fair enough, {first_name}! What's the typical evaluation cycle for [tools/vendors/partners] - annual, quarterly, or as-needed?"

Requirements:
- Base on timing_triggers data
- Ask about evaluation patterns
- Focus on WHEN not IF
- Shows you understand timing matters

4. BENCHMARK / VALUE-ADD (2 variants)
Pattern: Acknowledge + Offer specific benchmark data + No strings attached

Examples:
- "No worries at all, {first_name}! If helpful, I can share benchmarks on [specific KPI] for [industry/stage] companies - might be useful context even if we don't work together."
- "Understood, {first_name}! We recently analyzed [X] for [similar companies] - happy to share insights on [specific metric/challenge]. No pitch, just data."

Requirements:
- Offer specific, relevant benchmark
- Based on their stage/industry
- "No strings attached" tone
- Keep door open

5. ALTERNATIVE ANGLES (2-3 variants)
Pattern: Acknowledge + Pivot to different angle

Possible pivots based on situation:
- Pivot to Learning: "Got it, {first_name}! Out of curiosity - what's working well for you in [area]? Always learning from [their role]."
- Pivot to Referral: "Fair enough, {first_name}! Do you know anyone at {lead_company} who might handle [X]? Happy to connect."
- Pivot to Person: "Understood, {first_name}! Is there someone else at {lead_company} who handles [vendor decisions/tech partnerships]?"
- Pivot to Timing: "No problem, {first_name}! Would it make sense to circle back in [specific timeframe based on triggers]?"

Requirements:
- Natural pivot, not forced
- Based on analysis
- Keeps conversation open
- Low pressure

=== OUTPUT FORMAT ===

Return ONLY valid JSON:

{{
  "messages": [
    {{
      "id": 1,
      "type": "assumption_question",
      "message": "full ready-to-send message text",
      "assumption_basis": "what evidence from analysis supports this assumption",
      "expected_response": "what you hope to learn",
      "follow_up_if_yes": "what to say if assumption is correct",
      "follow_up_if_no": "what to say if assumption is wrong",
      "confidence": "high/medium/low that this will get response"
    }},
    {{
      "id": 2,
      "type": "clarification",
      "message": "full message text",
      "news_hook_used": "specific news item referenced",
      "pain_connection": "how news connects to pain point",
      "capability_mentioned": "specific Interexy capability",
      "confidence": "high/medium/low"
    }},
    {{
      "id": 3,
      "type": "future_focused",
      "message": "full message text",
      "timing_trigger_basis": "what trigger/pattern this is based on",
      "information_goal": "what you're trying to learn about timing",
      "confidence": "high/medium/low"
    }},
    {{
      "id": 4,
      "type": "benchmark",
      "message": "full message text",
      "benchmark_offered": "specific benchmark/data point",
      "value_to_lead": "why this would be useful to them",
      "confidence": "high/medium/low"
    }},
    {{
      "id": 5,
      "type": "alternative_angle",
      "message": "full message text",
      "pivot_type": "learning/referral/person/timing",
      "goal": "what you're trying to achieve",
      "confidence": "high/medium/low"
    }}
    ... (generate 12-15 total variants)
  ],
  
  "recommended_top_3": [
    {{
      "message_id": 1,
      "ranking": 1,
      "reasoning": "why this is #1 choice based on rejection type, lead profile, and research"
    }},
    {{
      "message_id": 5,
      "ranking": 2,
      "reasoning": "why this is #2 choice"
    }},
    {{
      "message_id": 8,
      "ranking": 3,
      "reasoning": "why this is #3 choice"
    }}
  ],
  
  "overall_strategy": {{
    "primary_approach": "which message type to lead with and why",
    "backup_approach": "if primary fails, try this next",
    "do_not_approaches": ["message types to avoid based on rejection analysis"],
    "timing_recommendation": "send now / wait X days / wait for specific trigger",
    "response_probability": "high/medium/low/very_low",
    "if_ignored_strategy": "what to do if this attempt also gets ignored"
  }},
  
  "conversation_continuation_plan": {{
    "if_they_respond_positively": "next step",
    "if_they_respond_neutrally": "next step",
    "if_they_ghost_again": "next step",
    "long_term_nurture": "how to stay on radar if not ready now"
  }},
  
  "notes": "Additional strategic notes based on full analysis"
}}

=== CRITICAL REQUIREMENTS ===

1. **Messages must be COMPLETE and READY TO SEND**
   - Start with acknowledgment: "Fair enough!" / "Understood!" / "No worries!" / "Got it!"
   - Keep SHORT: 2-4 sentences max
   - Natural, conversational tone
   - NO salesy language
   - Use first name: "{first_name}"

2. **Base EVERYTHING on REAL research**
   - Use actual news from deep_research
   - Use actual pain points from analysis
   - Use actual vendor approach hypothesis
   - Use actual timing triggers
   - If data missing, make reasonable inference but note it

3. **Match sophistication to lead's seniority**
   - C-level: High-level strategic questions
   - Director/VP: Operational challenges
   - Manager: Tactical questions

4. **Acknowledge rejection type appropriately**
   - Hard no → Respect it, offer value, exit gracefully
   - Soft no → One more angle, then respect
   - Bad timing → Focus on future triggers
   - Wrong person → Redirect

5. **Each message should feel DIFFERENT**
   - Vary opening acknowledgments
   - Different angles
   - Different tones
   - Different goals

6. **Confidence scoring**
   - High: Strong evidence, good timing, relevant
   - Medium: Some evidence, okay timing
   - Low: Weak evidence, poor timing, risky

7. **Return ONLY JSON** - no markdown blocks, no extra text

Current date: {datetime.now().strftime('%Y-%m-%d')}"""
    
    return prompt


def generate_messages(prompt):
    """Генерирует сообщения через OpenAI БЕЗ web search"""
    
    print(f"      💬 MESSAGE GENERATION через OpenAI (без web search)...")
    
    url = "https://api.openai.com/v1/responses"
    
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "gpt-4o",
        "tools": [],
        "input": prompt
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=180)
        
        if response.status_code != 200:
            print(f"      ❌ OpenAI error: {response.status_code}")
            return None
        
        data = response.json()
        
        # Извлекаем текст
        output_array = data.get('output', [])
        output_text = ""
        
        for item in output_array:
            if item.get('type') == 'message':
                content_array = item.get('content', [])
                for content_item in content_array:
                    if content_item.get('type') == 'output_text':
                        output_text = content_item.get('text', '')
                        break
                if output_text:
                    break
        
        if not output_text:
            return None
        
        # Парсим JSON
        output_text = output_text.replace('```json', '').replace('```', '').strip()
        json_start = output_text.find('{')
        json_end = output_text.rfind('}') + 1
        
        if json_start != -1 and json_end > json_start:
            output_text = output_text[json_start:json_end]
        
        messages_data = json.loads(output_text)
        print(f"      ✅ Messages готовы ({len(messages_data.get('messages', []))} вариантов)")
        return messages_data
        
    except Exception as e:
        print(f"      ❌ Error: {e}")
        return None


def save_batch_results(results):
    """Сохраняет результаты с ВСЕМИ вариантами сообщений"""
    
    batch_dir = "batch_no_thanks_results"
    if not os.path.exists(batch_dir):
        os.makedirs(batch_dir)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # === JSON ===
    json_filename = f"{batch_dir}/batch_no_thanks_{timestamp}.json"
    
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Full JSON: {json_filename}")
    
    # === SUMMARY TXT со ВСЕМИ вариантами ===
    txt_filename = f"{batch_dir}/batch_no_thanks_{timestamp}_summary.txt"
    
    with open(txt_filename, 'w', encoding='utf-8') as f:
        f.write("=" * 120 + "\n")
        f.write("BATCH NO THANKS PROCESSING - REJECTION HANDLING RESULTS\n")
        f.write("=" * 120 + "\n\n")
        
        f.write(f"Processed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total leads: {results['total_leads']}\n")
        f.write(f"Successful: {results['successful']}\n")
        f.write(f"Failed: {results['failed']}\n")
        f.write(f"Total cost: ~${results['estimated_cost']:.2f}\n\n")
        
        # === УСПЕШНЫЕ ЛИДЫ ===
        f.write("=" * 120 + "\n")
        f.write("SUCCESSFUL LEADS - DETAILED NO THANKS RESPONSE STRATEGIES\n")
        f.write("=" * 120 + "\n\n")
        
        for lead in results['leads']:
            if lead['status'] == 'success':
                f.write("\n" + "=" * 120 + "\n")
                f.write(f"LEAD: {lead['lead_name']} @ {lead['lead_company']}\n")
                f.write("=" * 120 + "\n\n")
                
                f.write(f"LinkedIn: {lead['linkedin_url']}\n")
                f.write(f"Position: {lead.get('lead_position', 'N/A')}\n")
                f.write(f"Qualification: {lead.get('qualification', 'N/A')} (Fit: {lead.get('fit_score', 0)}/10)\n")
                f.write(f"Vendor Readiness: {lead.get('vendor_readiness', 'N/A')}\n\n")
                
                # Rejection Analysis
                rejection = lead.get('rejection_analysis', {})
                f.write("-" * 120 + "\n")
                f.write("REJECTION ANALYSIS\n")
                f.write("-" * 120 + "\n")
                f.write(f"Type: {rejection.get('rejection_type', 'N/A')}\n")
                f.write(f"Confidence: {rejection.get('confidence', 'N/A')}\n")
                f.write(f"Evidence: {rejection.get('evidence', 'N/A')}\n")
                f.write(f"Recommended Approach: {rejection.get('recommended_approach', 'N/A')}\n\n")
                
                # Executive Summary
                f.write("-" * 120 + "\n")
                f.write("EXECUTIVE SUMMARY\n")
                f.write("-" * 120 + "\n")
                f.write(f"{lead.get('executive_summary', 'N/A')}\n\n")
                
                # === MESSAGES ===
                messages_data = lead.get('messages_data', {})
                messages = messages_data.get('messages', [])
                recommended_top_3 = messages_data.get('recommended_top_3', [])
                
                if messages:
                    f.write("=" * 120 + "\n")
                    f.write(f"FOLLOW-UP MESSAGE VARIANTS ({len(messages)} total)\n")
                    f.write("=" * 120 + "\n\n")
                    
                    # === TOP 3 RECOMMENDED ===
                    if recommended_top_3:
                        f.write("⭐ ⭐ ⭐  TOP 3 RECOMMENDED MESSAGES  ⭐ ⭐ ⭐\n\n")
                        
                        for rec in recommended_top_3:
                            msg_id = rec.get('message_id')
                            ranking = rec.get('ranking')
                            reasoning = rec.get('reasoning', 'N/A')
                            
                            # Находим само сообщение
                            msg_obj = next((m for m in messages if m.get('id') == msg_id), None)
                            
                            if msg_obj:
                                f.write(f"#{ranking}. MESSAGE ID: {msg_id} [{msg_obj.get('type', 'N/A').upper()}]\n")
                                f.write("-" * 120 + "\n")
                                f.write(f"{msg_obj.get('message', 'N/A')}\n\n")
                                f.write(f"💡 Why this is #{ranking}: {reasoning}\n")
                                f.write(f"📊 Confidence: {msg_obj.get('confidence', 'N/A').upper()}\n")
                                
                                # Дополнительная информация в зависимости от типа
                                if msg_obj.get('type') == 'assumption_question':
                                    f.write(f"🎯 Assumption basis: {msg_obj.get('assumption_basis', 'N/A')}\n")
                                    f.write(f"❓ Expected response: {msg_obj.get('expected_response', 'N/A')}\n")
                                elif msg_obj.get('type') == 'clarification':
                                    f.write(f"📰 News hook: {msg_obj.get('news_hook_used', 'N/A')}\n")
                                    f.write(f"🔗 Pain connection: {msg_obj.get('pain_connection', 'N/A')}\n")
                                elif msg_obj.get('type') == 'future_focused':
                                    f.write(f"⏰ Timing basis: {msg_obj.get('timing_trigger_basis', 'N/A')}\n")
                                    f.write(f"🎯 Information goal: {msg_obj.get('information_goal', 'N/A')}\n")
                                
                                f.write("\n" + "-" * 120 + "\n\n")
                    
                    # === ALL VARIANTS BY TYPE ===
                    f.write("\n" + "=" * 120 + "\n")
                    f.write("ALL MESSAGE VARIANTS BY TYPE\n")
                    f.write("=" * 120 + "\n\n")
                    
                    # Group by type
                    types = {}
                    for msg in messages:
                        msg_type = msg.get('type', 'other')
                        if msg_type not in types:
                            types[msg_type] = []
                        types[msg_type].append(msg)
                    
                    for msg_type, type_messages in sorted(types.items()):
                        f.write(f"\n{'▼' * 60}\n")
                        f.write(f"  {msg_type.upper().replace('_', ' ')} ({len(type_messages)} variants)\n")
                        f.write(f"{'▼' * 60}\n\n")
                        
                        for msg in type_messages:
                            f.write(f"#{msg.get('id', '?')}:\n")
                            f.write(f"{msg.get('message', 'N/A')}\n\n")
                            
                            # Type-specific details
                            if msg_type == 'assumption_question':
                                f.write(f"  Assumption basis: {msg.get('assumption_basis', 'N/A')}\n")
                                f.write(f"  Expected response: {msg.get('expected_response', 'N/A')}\n")
                                f.write(f"  If YES: {msg.get('follow_up_if_yes', 'N/A')}\n")
                                f.write(f"  If NO: {msg.get('follow_up_if_no', 'N/A')}\n")
                            elif msg_type == 'clarification':
                                f.write(f"  News hook: {msg.get('news_hook_used', 'N/A')}\n")
                                f.write(f"  Pain connection: {msg.get('pain_connection', 'N/A')}\n")
                                f.write(f"  Capability mentioned: {msg.get('capability_mentioned', 'N/A')}\n")
                            elif msg_type == 'future_focused':
                                f.write(f"  Timing trigger basis: {msg.get('timing_trigger_basis', 'N/A')}\n")
                                f.write(f"  Information goal: {msg.get('information_goal', 'N/A')}\n")
                            elif msg_type == 'benchmark':
                                f.write(f"  Benchmark offered: {msg.get('benchmark_offered', 'N/A')}\n")
                                f.write(f"  Value to lead: {msg.get('value_to_lead', 'N/A')}\n")
                            elif msg_type == 'alternative_angle':
                                f.write(f"  Pivot type: {msg.get('pivot_type', 'N/A')}\n")
                                f.write(f"  Goal: {msg.get('goal', 'N/A')}\n")
                            
                            f.write(f"  Confidence: {msg.get('confidence', 'N/A').upper()}\n")
                            f.write("\n" + "- " * 60 + "\n\n")
                    
                    # === OVERALL STRATEGY ===
                    strategy = messages_data.get('overall_strategy', {})
                    if strategy:
                        f.write("\n" + "=" * 120 + "\n")
                        f.write("OVERALL STRATEGY\n")
                        f.write("=" * 120 + "\n")
                        f.write(f"Primary approach: {strategy.get('primary_approach', 'N/A')}\n")
                        f.write(f"Backup approach: {strategy.get('backup_approach', 'N/A')}\n")
                        f.write(f"Do NOT use: {', '.join(strategy.get('do_not_approaches', ['N/A']))}\n")
                        f.write(f"Timing: {strategy.get('timing_recommendation', 'N/A')}\n")
                        f.write(f"Response probability: {strategy.get('response_probability', 'N/A').upper()}\n")
                        f.write(f"If ignored: {strategy.get('if_ignored_strategy', 'N/A')}\n\n")
                    
                    # === CONTINUATION PLAN ===
                    cont_plan = messages_data.get('conversation_continuation_plan', {})
                    if cont_plan:
                        f.write("-" * 120 + "\n")
                        f.write("CONVERSATION CONTINUATION PLAN\n")
                        f.write("-" * 120 + "\n")
                        f.write(f"If positive response: {cont_plan.get('if_they_respond_positively', 'N/A')}\n")
                        f.write(f"If neutral response: {cont_plan.get('if_they_respond_neutrally', 'N/A')}\n")
                        f.write(f"If ghost again: {cont_plan.get('if_they_ghost_again', 'N/A')}\n")
                        f.write(f"Long-term nurture: {cont_plan.get('long_term_nurture', 'N/A')}\n\n")
                    
                    # === STRATEGIC NOTES ===
                    notes = messages_data.get('notes', '')
                    if notes:
                        f.write("-" * 120 + "\n")
                        f.write("STRATEGIC NOTES\n")
                        f.write("-" * 120 + "\n")
                        f.write(f"{notes}\n\n")
                
                f.write("\n")
        
        # === FAILED LEADS ===
        if results['failed'] > 0:
            f.write("\n" + "=" * 120 + "\n")
            f.write("FAILED LEADS\n")
            f.write("=" * 120 + "\n\n")
            
            for lead in results['leads']:
                if lead['status'] == 'failed':
                    f.write(f"❌ {lead['linkedin_url']}\n")
                    f.write(f"   Reason: {lead.get('error', 'Unknown error')}\n\n")
        
        f.write("=" * 120 + "\n")
        f.write("END OF BATCH NO THANKS REPORT\n")
        f.write("=" * 120 + "\n")
    
    print(f"💾 Summary TXT: {txt_filename}")
    
    return json_filename, txt_filename


def process_single_lead(linkedin_url):
    """Обрабатывает одного лида: HeyReach → Analysis → Messages"""
    
    result = {
        'linkedin_url': linkedin_url,
        'status': 'failed',
        'lead_name': None,
        'lead_company': None,
        'lead_position': None,
        'error': None
    }
    
    # === ШАГ 1: HeyReach ===
    conversation = get_conversation_by_linkedin(linkedin_url)
    
    if not conversation:
        result['error'] = 'Conversation not found in HeyReach'
        return result
    
    correspondent = conversation.get('correspondentProfile', {})
    lead_name = f"{correspondent.get('firstName', '')} {correspondent.get('lastName', '')}".strip()
    lead_company = correspondent.get('companyName', 'Unknown')
    lead_position = correspondent.get('position', 'Unknown')
    
    result['lead_name'] = lead_name
    result['lead_company'] = lead_company
    result['lead_position'] = lead_position
    
    # === ШАГ 2: Deep Analysis с web search ===
    prompt, _, _ = create_full_no_thanks_analysis_prompt(conversation)
    analysis = analyze_with_openai(prompt, lead_name)
    
    if not analysis:
        result['error'] = 'Analysis failed'
        return result
    
    result['analysis'] = analysis
    result['qualification'] = analysis.get('qualification', {}).get('status', 'N/A')
    result['fit_score'] = analysis.get('qualification', {}).get('fit_score', 0)
    result['vendor_readiness'] = analysis.get('qualification', {}).get('vendor_readiness', 'N/A')
    result['executive_summary'] = analysis.get('executive_summary', '')
    result['rejection_analysis'] = analysis.get('conversation_analysis', {}).get('rejection_analysis', {})
    
    # === ШАГ 3: Message Generation БЕЗ web search ===
    metadata = {
        'lead_name': lead_name,
        'lead_company': lead_company,
        'lead_position': lead_position
    }
    
    msg_prompt = create_no_thanks_message_generation_prompt(analysis, metadata)
    messages_data = generate_messages(msg_prompt)
    
    if not messages_data:
        result['error'] = 'Message generation failed'
        return result
    
    result['messages_data'] = messages_data
    result['status'] = 'success'
    
    return result


# === MAIN FLOW ===

print("\n" + "=" * 100)
print("STEP 1: Загрузка списка лидов")
print("=" * 100)

linkedin_urls = load_leads_from_file('leads.txt')

if not linkedin_urls:
    print("\n❌ Нет лидов для обработки")
    exit(1)

print("\n" + "=" * 100)
print(f"STEP 2: Обработка {len(linkedin_urls)} лидов")
print("=" * 100)
print("⏳ Примерно 3-4 минуты на лид")
print("   (HeyReach → Deep Analysis с web search → No Thanks Messages)")
print()

results = {
    'processed_at': datetime.now().isoformat(),
    'total_leads': len(linkedin_urls),
    'successful': 0,
    'failed': 0,
    'estimated_cost': 0,
    'leads': []
}

start_time = time.time()

for idx, linkedin_url in enumerate(linkedin_urls, 1):
    print(f"\n{'='*100}")
    print(f"[{idx}/{len(linkedin_urls)}] Processing: {linkedin_url}")
    print(f"{'='*100}")
    
    lead_result = process_single_lead(linkedin_url)
    results['leads'].append(lead_result)
    
    if lead_result['status'] == 'success':
        results['successful'] += 1
        results['estimated_cost'] += 0.12  # ~$0.12 per lead (deep analysis)
        rejection_type = lead_result.get('rejection_analysis', {}).get('rejection_type', 'N/A')
        print(f"      ✅ SUCCESS: {lead_result['lead_name']} (Rejection: {rejection_type})")
    else:
        results['failed'] += 1
        print(f"      ❌ FAILED: {lead_result.get('error', 'Unknown')}")
    
    # Rate limiting
    if idx < len(linkedin_urls):
        print(f"\n      ⏸️  Пауза 5 секунд...")
        time.sleep(5)

elapsed_time = time.time() - start_time

print("\n" + "=" * 100)
print("STEP 3: Сохранение результатов")
print("=" * 100)

json_file, txt_file = save_batch_results(results)

print("\n" + "=" * 100)
print("✅ BATCH NO THANKS PROCESSING ЗАВЕРШЕН!")
print("=" * 100)

print(f"\n📊 СТАТИСТИКА:")
print(f"   Всего лидов: {results['total_leads']}")
print(f"   Успешно: {results['successful']} ✅")
print(f"   Не удалось: {results['failed']} ❌")
print(f"   Время: {int(elapsed_time/60)} мин {int(elapsed_time%60)} сек")
print(f"   Примерная стоимость: ${results['estimated_cost']:.2f}")

if results['successful'] > 0:
    print(f"\n📁 РЕЗУЛЬТАТЫ:")
    print(f"   • JSON (полный): {json_file}")
    print(f"   • TXT (со ВСЕМИ вариантами сообщений): {txt_file}")
    
    print(f"\n🎯 REJECTION TYPES:")
    rejection_counts = {}
    for lead in results['leads']:
        if lead['status'] == 'success':
            rej_type = lead.get('rejection_analysis', {}).get('rejection_type', 'unknown')
            rejection_counts[rej_type] = rejection_counts.get(rej_type, 0) + 1
    
    for rej_type, count in sorted(rejection_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"   • {rej_type}: {count} leads")

print("\n" + "=" * 100)
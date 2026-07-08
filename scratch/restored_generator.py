Created At: 2026-07-01T09:39:10Z
Completed At: 2026-07-01T09:39:10Z
File Path: `file:///c:/Users/user/Downloads/Cadence/Cadence/content/generator.py`
Total Lines: 2114
Total Bytes: 108300
Showing lines 630 to 920
The following code has been modified to include a line number before every line, in the format: <line_number>: <original_line>. Please note that any changes targeting the original code should remove the line number, colon, and leading space.
630: <h2>Conclusion</h2>
631: <p>Keeping things simple is the key to success. Focus on action, learn from your mistakes, and keep moving forward.</p>"""
632:         
633:         return {
634:             "title": f"The Guide to {title}",
635:             "meta_description": f"Learn the core strategies, implementation steps, and best practices for {title} in this comprehensive and practical guide.",
636:             "category": "General Business",
637:             "tags": ["guide", "strategy", "planning", "success"],
638:             "excerpt": f"A detailed guide to mastering {title}. Explore core principles, step-by-step workflows, trade-offs, and strategies for success.",
639:             "body": body
640:         }
641: 
642: 
643: def generate_via_gemini(system_prompt: str, user_prompt: str) -> dict:
644:     """Calls Google Gemini API using requests."""
645:     import requests
646:     import json
647:     
648:     api_key = config('GEMINI_API_KEY', default=config('GOOGLE_API_KEY', default=None))
649:     if not api_key:
650:         raise ValueError("GEMINI_API_KEY is not configured.")
651:         
652:     url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
653:     headers = {'Content-Type': 'application/json'}
654:     
655:     combined_prompt = f"{system_prompt}\n\n{user_prompt}"
656:     
657:     payload = {
658:         "contents": [{
659:             "parts": [{
660:                 "text": combined_prompt
661:             }]
662:         }],
663:         "generationConfig": {
664:             "responseMimeType": "application/json",
665:             "responseSchema": {
666:                 "type": "OBJECT",
667:                 "properties": {
668:                     "title": {"type": "STRING"},
669:                     "meta_description": {"type": "STRING"},
670:                     "category": {"type": "STRING"},
671:                     "tags": {
672:                         "type": "ARRAY",
673:                         "items": {"type": "STRING"}
674:                     },
675:                     "excerpt": {"type": "STRING"},
676:                     "body": {"type": "STRING"}
677:                 },
678:                 "required": ["title", "meta_description", "category", "tags", "excerpt", "body"]
679:             }
680:         }
681:     }
682:     
683:     response = requests.post(url, headers=headers, json=payload, timeout=60)
684:     response.raise_for_status()
685:     result = response.json()
686:     
687:     try:
688:         text_content = result['candidates'][0]['content']['parts'][0]['text']
689:         content = json.loads(text_content.strip())
690:         content['generation_prompt'] = user_prompt
691:         content['ai_model'] = 'gemini-1.5-flash'
692:         return content
693:     except (KeyError, IndexError, ValueError) as e:
694:         logger.error(f"Failed to parse Gemini response: {e}")
695:         raise ValueError("Invalid response format from Gemini")
696: 
697: 
698: def generate_social_via_gemini(system_prompt: str, user_prompt: str) -> dict:
699:     """Calls Google Gemini API for social media post generation."""
700:     import requests
701:     import json
702:     
703:     api_key = config('GEMINI_API_KEY', default=config('GOOGLE_API_KEY', default=None))
704:     if not api_key:
705:         raise ValueError("GEMINI_API_KEY is not configured.")
706:         
707:     url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
708:     headers = {'Content-Type': 'application/json'}
709:     
710:     combined_prompt = f"{system_prompt}\n\n{user_prompt}"
711:     
712:     payload = {
713:         "contents": [{
714:             "parts": [{
715:                 "text": combined_prompt
716:             }]
717:         }],
718:         "generationConfig": {
719:             "responseMimeType": "application/json",
720:             "responseSchema": {
721:                 "type": "OBJECT",
722:                 "properties": {
723:                     "title": {"type": "STRING"},
724:                     "body": {"type": "STRING"},
725:                     "excerpt": {"type": "STRING"},
726:                     "tags": {
727:                         "type": "ARRAY",
728:                         "items": {"type": "STRING"}
729:                     },
730:                     "meta_description": {"type": "STRING"}
731:                 },
732:                 "required": ["title", "body", "excerpt", "tags", "meta_description"]
733:             }
734:         }
735:     }
736:     
737:     response = requests.post(url, headers=headers, json=payload, timeout=60)
738:     response.raise_for_status()
739:     result = response.json()
740:     
741:     try:
742:         text_content = result['candidates'][0]['content']['parts'][0]['text']
743:         content = json.loads(text_content.strip())
744:         content['generation_prompt'] = user_prompt
745:         content['ai_model'] = 'gemini-1.5-flash'
746:         return content
747:     except (KeyError, IndexError, ValueError) as e:
748:         logger.error(f"Failed to parse Gemini response: {e}")
749:         raise ValueError("Invalid response format from Gemini")
750: 
751: 
752: def generate_blog_post(idea: ContentIdea, website: Website) -> dict:
753:     """
754:     Generates a high-quality blog post using a 2-Layer Architecture:
755:     Layer 1: Generate a highly structured, strategic content outline based on live search and site context.
756:     Layer 2: Expand the outline into a deep, human-sounding B2B/B2C blog post with clean HTML styling.
757:     """
758:     # 1. Perform live search for up-to-date facts, statistics, and industry context
759:     logger.info(f"Layer 1: Performing live search for topic: {idea.title}")
760:     live_data = search_live_data(idea.title)
761:     
762:     # 2. Load website writing style reference samples (if uploaded by user)
763:     style_reference = get_style_reference_samples(website, 'blog')
764: 
765:     target_keywords = (
766:         ", ".join(idea.meta_tags)
767:         if idea.meta_tags
768:         else "Auto-select relevant keywords"
769:     )
770: 
771:     system_prompt = build_system_prompt(website, 'blog')
772:     import json
773: 
774:     # ==========================================
775:     # LAYER 1: STRATEGIC OUTLINE GENERATOR
776:     # ==========================================
777:     logger.info(f"Layer 1: Generating blog content outline for: {idea.title}")
778:     layer1_user_prompt = f"""
779: You are a senior content strategist and SEO architect.
780: Create a highly structured blog post outline for {website.name} ({website.domain}).
781: 
782: Topic: {idea.title}
783: Context: {idea.context or "None provided"}
784: Target Keywords: {target_keywords}
785: Verified Search Data (Use real facts/stats from here):
786: {live_data}
787: 
788: Reference Samples (Match formatting structure):
789: {style_reference}
790: 
791: Outline Guidelines:
792: 1. Editorial Headings: Do NOT use generic headings like "Introduction", "Conclusion", "What is X", or "Benefits of X". Plan editorial, high-authority headings that reflect choices, operational realities, or tradeoffs (e.g. "The Friction of Integrating...", "Why Standard Metrics Fail").
793: 2. Flow: Plan 4-6 distinct content sections. Ensure each section adds new value.
794: 3. Content Details: For each section, list 3-5 specific bullet points or concepts to cover. Highlight where to use verified search stats.
795: 4. Word Count: Plan the word count distribution targeting 900-1300 words overall.
796: 
797: Return ONLY valid JSON in the following format:
798: {{
799:   "post_title": "Proposed practitioner-level post title",
800:   "recommended_category": "Short category name",
801:   "tags": ["tag1", "tag2"],
802:   "sections": [
803:     {{
804:       "heading": "Section Heading",
805:       "focus_points": ["bullet point 1", "bullet point 2"],
806:       "estimated_words": 200
807:     }}
808:   ]
809: }}
810: """
811:     try:
812:         layer1_response = client.chat.completions.create(
813:             model=MODEL,
814:             messages=[
815:                 {'role': 'system', 'content': "You are an expert B2B/B2C content strategist. You plan structured, SEO-optimized outlines."},
816:                 {'role': 'user', 'content': layer1_user_prompt}
817:             ],
818:             temperature=0.4,
819:             response_format={"type": "json_object"}
820:         )
821:         outline_data = json.loads(layer1_response.choices[0].message.content.strip())
822:         logger.info(f"Layer 1: Outline successfully generated: {outline_data.get('post_title')}")
823:     except Exception as layer1_err:
824:         logger.error(f"Layer 1: Outline generation failed: {layer1_err}. Falling back to default layout.")
825:         outline_data = {
826:             "post_title": idea.title,
827:             "recommended_category": "Technology",
828:             "tags": ["Technology", "Industry Insights"],
829:             "sections": [
830:                 {"heading": f"The State of {idea.title} Today", "focus_points": ["Current challenges", "Why this topic matters now"], "estimated_words": 250},
831:                 {"heading": "Key Tradeoffs and Implementation Hurdles", "focus_points": ["Decisions to make", "Common pitfalls to avoid"], "estimated_words": 300},
832:                 {"heading": "Practical Next Steps for Teams", "focus_points": ["Actionable workflows", "Success metrics"], "estimated_words": 250}
833:             ]
834:         }
835: 
836:     # ==========================================
837:     # LAYER 2: ARTICLE EXPANSION & COPYWRITER
838:     # ==========================================
839:     logger.info(f"Layer 2: Expanding outline into full blog draft for: {outline_data.get('post_title')}")
840:     
841:     sections_json_str = json.dumps(outline_data.get('sections', []), indent=2)
842:     
843:     layer2_user_prompt = f"""
844: You are a senior editorial writer and B2B subject matter expert.
845: Write a deep-dive, original blog post based on this planned outline.
846: 
847: ==================================
848: PLANNING OUTLINE (Follow this structure)
849: ==================================
850: Proposed Title: {outline_data.get('post_title')}
851: Recommended Category: {outline_data.get('recommended_category')}
852: Planned Sections:
853: {sections_json_str}
854: 
855: ==================================
856: CONTEXT & RESEARCH
857: ==================================
858: Target Keywords: {target_keywords}
859: Verified Search Data:
860: {live_data}
861: 
862: ==================================
863: WRITING DIRECTIVES (CRITICAL: SOUND HUMAN)
864: ==================================
865: 1. Pacing & Sentence Variation:
866:    - Vary sentence and paragraph lengths. Mix short, punchy sentences with longer ones. Use occasional single-sentence paragraphs.
867:    - Ground everything in operational reality, decisions, and workflows rather than broad theory.
868:    - Do NOT use direct personal pronouns that claim personal experience (no "I have found", "my team did"). Keep it objective, professional, and authoritative.
869: 
870: 2. Zero AI Clichés & Buzzwords:
871:    - Strictly avoid: leverage, optimize, enhance, transform, facilitate, streamline, robust, innovation, impactful, cutting-edge, powerful, seamless, revolutionize, groundbreaking, synergy, enable, empower, accelerate, redefine, or next-generation.
872:    - Do NOT use generic AI transition phrases (e.g. "Furthermore", "Moreover", "Ultimately", "In conclusion", "As a result", "Therefore").
873: 
874: 3. HTML Formatting:
875:    - Use clean, standard HTML containing ONLY h2, h3, p, ul, ol, li, strong, a, and blockquote.
876:    - Do NOT include markdown styling (like `**bold**` or `# heading`) inside the HTML body. Use HTML tags for all styling.
877: 
878: 4. SEO & Authority:
879:    - Ground assertions in the "Verified Search Data" provided. Never fabricate statistics.
880:    - Integrate target keywords naturally into the text.
881: 
882: ==================================
883: OUTPUT REQUIREMENT
884: ==================================
885: Return ONLY valid JSON in the following format:
886: {{
887:   "title": "Final post title",
888:   "meta_description": "Natural SEO meta description under 160 characters",
889:   "category": "Single-word or short phrase category (e.g., Marketing, Engineering)",
890:   "tags": ["tag1", "tag2"],
891:   "excerpt": "A clean, plain-text summary (150-200 characters) for the preview card",
892:   "body": "Your full, deep-dive article body in clean HTML format"
893: }}
894: """
895:     try:
896:         layer2_response = client.chat.completions.create(
897:             model=MODEL,
898:             messages=[
899:                 {'role': 'system', 'content': system_prompt},
900:                 {'role': 'user', 'content': layer2_user_prompt}
901:             ],
902:             temperature=0.7,
903:             response_format={"type": "json_object"}
904:         )
905:         content = json.loads(layer2_response.choices[0].message.content.strip())
906:         content['generation_prompt'] = layer2_user_prompt
907:         content['ai_model'] = MODEL
908:         logger.info(f"Layer 2: Article expanded successfully: {content.get('title')} ({len(content.get('body', ''))} chars)")
909:         return content
910:     except Exception as e:
911:         logger.error(f"Layer 2: Article expansion failed: {e}")
912:         fallback_content = get_rich_fallback_blog(idea.title)
913:         fallback_content['generation_prompt'] = layer2_user_prompt
914:         fallback_content['ai_model'] = 'local-fallback'
915:         return fallback_content
916: 
917: 
918: def generate_social_post(idea: ContentIdea, website: Website, platform: str) -> dict:
919:     """Generates platform-specific social media content using user-provided samples."""
920:     system_prompt = build_system_prompt(website, platform)
The above content does NOT show the entire file contents. If you need to view any lines of the file which were not shown to complete your task, call this tool again to view those lines.

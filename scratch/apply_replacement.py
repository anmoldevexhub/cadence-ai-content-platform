import os
import sys

def main():
    file_path = 'content/generator.py'
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found!")
        sys.exit(1)

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    start_marker = "def generate_blog_post(idea: ContentIdea, website: Website) -> dict:"
    end_marker = "def generate_social_post(idea: ContentIdea, website: Website, platform: str) -> dict:"

    start_idx = content.find(start_marker)
    end_idx = content.find(end_marker)

    if start_idx == -1:
        print("Error: Could not find start marker 'def generate_blog_post'")
        sys.exit(1)
    if end_idx == -1:
        print("Error: Could not find end marker 'def generate_social_post'")
        sys.exit(1)

    new_blog_code = """def generate_blog_post(idea: ContentIdea, website: Website) -> dict:
    \"\"\"Generates a full blog post using a single prompt approach.\"\"\"
    # Get live search data
    logger.info(f"Performing live search for topic: {idea.title}")
    live_data = search_live_data(idea.title)
    
    # Get user-uploaded samples (NOT from crawler)
    style_reference = get_style_reference_samples(website, 'blog')

    target_keywords = (
        ", ".join(idea.meta_tags)
        if idea.meta_tags
        else "Auto-select relevant keywords"
    )

    system_prompt = build_system_prompt(website, 'blog')
    import json
    
    user_prompt = f\"\"\"
You are a senior content strategist, editor, and SEO writer.

Write an ORIGINAL blog post for {website.name}.

INPUT

Topic: {idea.title}
Context: {idea.context or "None provided"}
Target Keywords: {target_keywords}

Reference Samples:
{style_reference}

Verified Search Data:
{live_data}

GOAL

Create an editorial-quality blog that feels written by an experienced human writer.

Study the reference samples and learn:

* tone
* formatting
* pacing
* reading level
* CTA placement

Learn patterns only.
Do not imitate wording.

CONTENT

* Length: 900–1300 words
* Match search intent
* Use clear H2/H3 headings
* Keep paragraph lengths varied
* Each section must contribute new information
* Prefer practical insight over broad explanation
* Use operational examples where useful
* Explain ideas through situations, observations, and outcomes
* Do not force examples into every section

INTRODUCTION

Start close to the reader's real problem.

Choose one:

* business observation
* practical problem
* realistic situation

Do NOT begin with:

* broad industry statements
* definitions
* future predictions
* "In today's world"
* "Every day, businesses..."
* "AI is changing..."
* "Imagine a world..."

SECTION FLOW

Do not use one fixed structure across the entire article.

Different sections may use:

* observation → explanation
* problem → impact
* example → learning
* situation → outcome
* insight → recommendation

Some sections may:

* be short
* focus on one idea
* skip examples

Prioritize natural reading flow over perfect symmetry.

Do NOT expose internal writing labels.

Never output headings or phrases such as:

* Situation
* Explanation
* Outcome
* Insight
* Example
* Implementation Advice
* Call to Action

Use them internally only.

SPECIFICITY

Avoid generic actors:

* a company
* businesses
* organizations

Prefer:

* teams
* departments
* workflows
* operational situations

Describe:

* what changed
* why it mattered
* what happened next

LANGUAGE

Write in clear business English.

Target approximately Grade 7–9 reading level.

Prefer:

* common words
* shorter sentences
* direct explanations

If a simpler word works, use it.

Avoid:

* academic tone
* motivational tone
* corporate jargon
* abstract language
* dramatic technology framing

Avoid repeated words such as:
leverage
optimize
enhance
transform
facilitate
streamline
robust
innovation
impactful
cutting-edge
powerful
seamless
revolutionize
significant
groundbreaking

AUTHORITY

Use statistics only from Verified Search Data.

Never invent numbers.

If no verified data exists:
use examples instead.

SEO

* Use target keywords naturally
* Include related concepts naturally
* Avoid keyword stuffing
* Prioritize readability

BRAND

Mention {website.name} only if naturally relevant.
Maximum one mention.

CTA

End with practical next steps.

Do not sound promotional.

OUTPUT

Return ONLY valid JSON.

{{
"title":"",
"meta_description":"",
"category":"",
"tags":[],
"excerpt":"",
"body":"clean HTML only"
}}
\"\"\"

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt}
            ],
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        content = json.loads(response.choices[0].message.content.strip())
        content['generation_prompt'] = user_prompt
        content['ai_model'] = MODEL
        return content
    except Exception as e:
        logger.error(f"Failed to generate blog post with single prompt: {e}")
        fallback_content = get_rich_fallback_blog(idea.title)
        fallback_content['generation_prompt'] = user_prompt
        fallback_content['ai_model'] = 'local-fallback'
        return fallback_content"""

    new_content = content[:start_idx] + new_blog_code + "\n\n" + content[end_idx:]

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print("Successfully replaced generate_blog_post in content/generator.py!")

if __name__ == '__main__':
    main()

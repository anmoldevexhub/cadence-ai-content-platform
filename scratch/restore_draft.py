import os
import django
import sys

sys.stdout.reconfigure(encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cadence_project.settings')
django.setup()

from content.models import ContentDraft

draft = ContentDraft.objects.get(pk=278)

original_body = """<h2>Understanding GST Returns in India</h2>
<p>The Goods and Services Tax (GST) is a crucial aspect of India’s taxation system, simplifying the tax structure and ensuring transparency. However, when it comes to filing GST returns, many find it challenging. This guide will walk you through the process, breaking it down into manageable steps.</p>

<h2>What Are GST Returns?</h2>
<p>GST returns are periodic statements that taxpayers submit to report their income, sales, purchases, and the amount of tax collected and paid. These returns help the government track tax compliance and ensure that taxpayers fulfill their obligations.</p>

<h3>Types of GST Returns</h3>
<ul>
<li><strong>GSTR-1:</strong> This return is filed by every registered taxpayer to report sales.</li>
<li><strong>GSTR-2:</strong> A return that reflects the purchases made by the taxpayer (currently suspended).</li>
<li><strong>GSTR-3B:</strong> A summary return filed monthly that includes the details of sales and purchases, along with the payment of tax.</li>
<li><strong>GSTR-9:</strong> An annual return filed by regular taxpayers, consolidating the monthly returns filed throughout the year.</li>
<li><strong>GSTR-10:</strong> Filed by taxpayers whose GST registration has been canceled.</li>
</ul>

<h2>Steps to File GST Returns</h2>
<p>Filing your GST returns involves several steps. Here’s how to do it effectively:</p>

<h3>1. Gather Required Documents</h3>
<p>Before you start, collect all necessary documents, including:</p>
<ul>
<li>Sales and purchase invoices</li>
<li>Tax payment receipts</li>
<li>Bank statements</li>
<li>Any other relevant financial documents</li>
</ul>

<h3>2. Log into the GST Portal</h3>
<p>Access the official GST Portal (<a href='https://www.gst.gov.in' target='_blank'>gst.gov.in</a>) and log in using your credentials. If you don’t have an account, you will need to register.</p>

<h3>3. Select the Appropriate Return</h3>
<p>Choose the specific return you need to file. For most businesses, GSTR-3B is the monthly summary return that needs to be submitted.</p>

<h3>4. Fill in the Details</h3>
<p>Carefully input the required details:</p>
<ul>
<li>Sales data</li>
<li>Purchases data</li>
<li>Input tax credit details</li>
<li>Any adjustments, if applicable</li>
</ul>

<h3>5. Review and Validate</h3>
<p>Double-check all the information you’ve entered. Use the “Validate” option on the portal to ensure there are no errors. This step is crucial to avoid penalties.</p>

<h3>6. Submit the Return</h3>
<p>Once you’re confident everything is accurate, submit the return. A confirmation message will appear, and you’ll receive an acknowledgment slip.</p>

<h3>7. Pay Any Tax Due</h3>
<p>If you owe tax, make the payment through the portal. Ensure that you do this before the due date to avoid late fees.</p>

<h2>Common Mistakes to Avoid</h2>
<p>Filing GST returns can be tricky, and mistakes can lead to penalties. Here are common pitfalls to watch out for:</p>
<ul>
<li>Missing deadlines: Always keep track of due dates for each return type.</li>
<li>Inaccurate data entry: Ensure that all figures are correct to avoid discrepancies.</li>
<li>Neglecting input tax credits: Claim all eligible credits to reduce your tax liability.</li>
<li>Not keeping proper records: Maintain thorough documentation to support your returns.</li>
</ul>

<h2>Final Thoughts</h2>
<p>Filing GST returns in India doesn’t have to be overwhelming. By following these steps and maintaining good records, you can ensure compliance and avoid potential pitfalls. If you need further assistance, consider reaching out to a professional or enrolling in GST training courses.</p>

<h3>Enquire Now</h3>
<p>For more information on GST filing and training, <a href='mailto:info@techvigya.com'>contact us</a>. Let our team of experts guide you through the process!</p>"""

draft.body = original_body
draft.save()
print("Draft 278 body restored successfully.")

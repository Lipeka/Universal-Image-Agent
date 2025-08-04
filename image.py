import io
import base64
import streamlit as st
from PIL import Image
from langgraph.graph import StateGraph, END
from openai import OpenAI
client = OpenAI(
    api_key="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",  # <-- put your OpenRouter key here
    base_url="https://openrouter.ai/api/v1"
)
MODEL = "qwen/qwen2.5-vl-32b-instruct:free"
UNIVERSAL_PROMPT = """
You are an expert multimodal AI assistant trained to extract and analyze information from visual content including charts, tables, and documents.

You will receive:
- An image (which may be a time series forecast, Prophet plot, bar chart, table, etc.)
- A user instruction (e.g., extract data, summarize, compare series)

Follow these rules:

1. If the image is a Prophet forecast chart or any time series plot:
   - Extract **all visible data points** as:
     | Date       | Series Name | Value |
     |------------|-------------|-------|
     | YYYY-MM-DD | series_name | 123   |
   - Detect if **multiple series** are present. Include them all and distinguish clearly by `Series Name`.
   - If the user asks for a **specific time period** (e.g., "March 2023", "last 7 days", or "between Jan and Apr 2024"):
     - Return only those filtered rows.
   - Add a summary section:
     - **Max Value:** <value> on <date>  
     - **Min Value:** <value> on <date>
   - If time range spans weeks or months:
     - Provide **weekly or monthly average trends** as:
       | Week Starting | Avg Value |
       |---------------|-----------|
     - OR  
       | Month         | Avg Value |
       |---------------|-----------|

2. If the image is a bar chart, line chart, pie chart, histogram, etc:
   - Extract all values shown in the visualization.
   - For bar/pie: list category and value.
   - For line charts: list (x, y) points, series-wise.
   - If multiple series exist (e.g., "Sales vs Profit"), include both in the table with separate series names.
   - Output in Markdown tables:
     | Category | Series A | Series B |
     |----------|----------|----------|

3. If the image is a table:
   - OCR the entire table and reformat it as a **Markdown table**.
   - Preserve all row/column headers and structure.

4. If the image is a document, UI, or photo (not chart):
   - Perform **Visual Question Answering**.
   - Use text (OCR), icons, layout, and context to respond.
   - Quote visible text or labels as needed.

General Guidelines:
- Return only data **visible** in the image — no guessing.
- Clearly separate **summaries**, **filtered results**, and **full tables**.
- Use Markdown for tables.
- If values are unreadable, mark them as `"N/A"`.

Do not explain your process. Respond with summary + table(s) only.
"""
class UniversalAgent:
    def __init__(self, model=MODEL):
        self.model = model
    def run(self, state):
        question = state["question"].strip()
        image = state["image"]
        if not question:
            state["answer"] = "⚠️ Please enter a valid question."
            return state
        img_bytes = io.BytesIO()
        image.save(img_bytes, format="PNG")
        img_base64 = base64.b64encode(img_bytes.getvalue()).decode("utf-8")
        img_data_url = f"data:image/png;base64,{img_base64}"
        full_prompt = f"{UNIVERSAL_PROMPT}\n\nUser instruction: {question}"
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": full_prompt},
                        {"type": "image_url", "image_url": {"url": img_data_url}}
                    ]
                }
            ]
        )
        state["answer"] = response.choices[0].message.content
        return state
st.set_page_config(page_title="🖼️ Universal Image Agent", layout="wide")
st.title("🖼️Image Agent")
uploaded_file = st.file_uploader("Upload an image:", type=["jpg", "jpeg", "png"])
question = st.text_area("Ask a question (e.g., 'Show all data points', 'Who is in the image?'):")
if uploaded_file and st.button("Ask"):
    if not question.strip():
        st.error("⚠️ Please enter a valid question.")
    else:
        image = Image.open(uploaded_file)
        graph = StateGraph(dict)
        graph.add_node("agent", UniversalAgent().run)
        graph.set_entry_point("agent")
        graph.add_edge("agent", END)
        with st.spinner("Analyzing..."):
            final_state = graph.compile().invoke({
                "question": question,
                "image": image
            })
            st.subheader("🔹 Answer")
            st.markdown(final_state["answer"])


from pathlib import Path
import sqlite3
import sys

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "generated" / "full" / "traceforge.db"

sys.path.insert(0, str(ROOT / "src"))

from traceforge.copilot import (
    answer_with_ollama,
    retrieve_evidence,
)

from traceforge.capa_service import (
    get_capa,
    transition_capa,
    record_verification_evidence,
)
st.set_page_config(
    page_title="TraceForge AI | Manufacturing Intelligence",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .block-container {padding-top: 1.5rem;}
    [data-testid="stMetric"] {
        background: rgba(100, 116, 139, 0.08);
        padding: 16px;
        border-radius: 12px;
        border: 1px solid rgba(128, 128, 128, 0.18);
    }
    .main-title {font-size: 2.1rem; font-weight: 750;}
    .sub-title {color: #8b95a5; margin-bottom: 1.5rem;}
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=30)
def read_query(sql, params=()):
    with sqlite3.connect(DB_PATH) as connection:
        return pd.read_sql_query(sql, connection, params=params)


def scalar(sql):
    df = read_query(sql)
    return df.iloc[0, 0] if not df.empty else 0


def money_or_number(value):
    return f"{int(value):,}"


if not DB_PATH.exists():
    st.error(f"Database not found: {DB_PATH}")
    st.info("Generate the starter dataset first.")
    st.stop()


# Sidebar
st.sidebar.title("🏭 TraceForge AI")
st.sidebar.caption("Manufacturing Intelligence Platform")
st.sidebar.divider()

page = st.sidebar.radio(
    "Navigation",
    [
        "Overview",
        "Defect Traceability",
        "Production Investigation",
        "Supplier Quality",
        "CAPA Management",
        "TraceForge Copilot",
    ],
)

st.sidebar.divider()
st.sidebar.caption("Dataset: Full")
st.sidebar.caption("Database: SQLite")
st.sidebar.caption("Data refresh: 30 seconds")

st.markdown('<div class="main-title">TraceForge AI</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">End-to-end manufacturing traceability and quality intelligence</div>',
    unsafe_allow_html=True,
)


if page == "Overview":

    st.header("Manufacturing Overview")

    total_orders = scalar(
        "SELECT COUNT(*) FROM production_orders"
    )
    total_products = scalar(
        "SELECT COUNT(*) FROM products"
    )
    total_suppliers = scalar(
        "SELECT COUNT(*) FROM suppliers"
    )
    total_inspections = scalar(
        "SELECT COUNT(*) FROM inspection_results"
    )
    total_inspected = scalar(
        "SELECT COALESCE(SUM(inspected_quantity), 0) FROM inspection_results"
    )
    total_defective = scalar(
        "SELECT COALESCE(SUM(defective_quantity), 0) FROM inspection_results"
    )
    total_defects = scalar(
        "SELECT COUNT(*) FROM defects"
    )
    open_capas = scalar(
        "SELECT COUNT(*) FROM corrective_actions WHERE status != 'CLOSED'"
    )

    defect_rate = (
        total_defective / total_inspected * 100
        if total_inspected else 0
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Production Orders", money_or_number(total_orders))
    c2.metric("Products", money_or_number(total_products))
    c3.metric("Inspections", money_or_number(total_inspections))
    c4.metric("Suppliers", money_or_number(total_suppliers))

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Units Inspected", money_or_number(total_inspected))
    c6.metric("Defective Units", money_or_number(total_defective))
    c7.metric("Defect Rate", f"{defect_rate:.2f}%")
    c8.metric("Open CAPAs", money_or_number(open_capas))

    st.divider()

    left, right = st.columns(2)

    with left:
        st.subheader("Production Order Status")

        order_status = read_query("""
            SELECT status, COUNT(*) AS total
            FROM production_orders
            GROUP BY status
            ORDER BY total DESC
        """)

        if not order_status.empty:
            fig = px.pie(
                order_status,
                names="status",
                values="total",
                hole=0.55,
                title="Order Distribution",
            )
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("No production orders available.")

    with right:
        st.subheader("Defects by Severity")

        severity = read_query("""
            SELECT severity, COUNT(*) AS total
            FROM defects
            GROUP BY severity
            ORDER BY CASE severity
                WHEN 'CRITICAL' THEN 1
                WHEN 'HIGH' THEN 2
                WHEN 'MEDIUM' THEN 3
                ELSE 4
            END
        """)

        if not severity.empty:
            fig = px.bar(
                severity,
                x="severity",
                y="total",
                color="severity",
                title="Defect Severity Distribution",
            )
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("No defects available.")

    left, right = st.columns(2)

    with left:
        st.subheader("Inspection Results")

        inspections = read_query("""
            SELECT result, COUNT(*) AS total
            FROM inspection_results
            GROUP BY result
        """)

        if not inspections.empty:
            fig = px.bar(
                inspections,
                x="result",
                y="total",
                color="result",
                title="Pass vs Fail",
            )
            st.plotly_chart(fig, width="stretch")

    with right:
        st.subheader("CAPA Status")

        capa_status = read_query("""
            SELECT status, COUNT(*) AS total
            FROM corrective_actions
            GROUP BY status
        """)

        if not capa_status.empty:
            fig = px.pie(
                capa_status,
                names="status",
                values="total",
                hole=0.5,
                title="Corrective Action Lifecycle",
            )
            st.plotly_chart(fig, width="stretch")

    st.subheader("Recent Defects")

    recent = read_query("""
        SELECT
            d.defect_id,
            d.defect_type,
            d.severity,
            d.affected_quantity,
            d.disposition,
            d.order_id,
            p.name AS product_name
        FROM defects d
        JOIN production_orders po ON po.order_id = d.order_id
        JOIN products p ON p.sku = po.sku
        ORDER BY d.defect_id DESC
        LIMIT 10
    """)

    st.dataframe(recent, width="stretch", hide_index=True)


elif page == "Defect Traceability":

    st.header("End-to-End Defect Traceability")
    st.write(
        "Follow a manufacturing defect from inspection "
        "through production, machinery, material lots and suppliers."
    )

    defects = read_query("""
        SELECT defect_id
        FROM defects
        ORDER BY defect_id
    """)

    if defects.empty:
        st.warning("No defects are available.")
        st.stop()

    defect_id = st.selectbox(
        "Select Defect ID",
        defects["defect_id"].tolist(),
    )

    trace = read_query("""
        SELECT
            d.defect_id,
            d.defect_type,
            d.severity,
            d.affected_quantity,
            d.disposition,

            ir.inspection_id,
            ir.inspected_at,
            ir.inspected_quantity,
            ir.defective_quantity,
            ir.result AS inspection_result,

            po.order_id,
            po.planned_quantity,
            po.start_date,
            po.end_date,
            po.status AS order_status,

            p.sku,
            p.name AS product_name,
            p.category,

            ps.step_id,
            ps.step_number,
            ps.process_name,
            ps.temperature,
            ps.pressure,
            ps.status AS process_status,

            m.machine_id,
            m.machine_name,
            m.process_type,

            ml.lot_id,
            ml.material_code,
            ml.received_date,
            ml.quantity_received,

            s.supplier_id,
            s.name AS supplier_name,
            s.country,
            s.risk_tier

        FROM defects d
        JOIN inspection_results ir
            ON ir.inspection_id = d.inspection_id
        JOIN production_orders po
            ON po.order_id = d.order_id
        JOIN products p
            ON p.sku = po.sku
        LEFT JOIN process_steps ps
            ON ps.step_id = d.step_id
        LEFT JOIN machines m
            ON m.machine_id = ps.machine_id
        LEFT JOIN material_lots ml
            ON ml.lot_id = d.lot_id
        LEFT JOIN suppliers s
            ON s.supplier_id = ml.supplier_id

        WHERE d.defect_id = ?
    """, (defect_id,))

    if trace.empty:
        st.error("Trace record could not be found.")
        st.stop()

    record = trace.iloc[0]

    a, b, c, d = st.columns(4)
    a.metric("Defect", record["defect_id"])
    b.metric("Severity", record["severity"])
    c.metric("Affected Units", int(record["affected_quantity"]))
    d.metric("Disposition", record["disposition"])

    st.divider()

    st.subheader("Traceability Chain")

    stages = [
        ("1. Inspection", record["inspection_id"]),
        ("2. Defect", record["defect_id"]),
        ("3. Production Order", record["order_id"]),
        ("4. Process Step", record["step_id"]),
        ("5. Machine", record["machine_id"]),
        ("6. Material Lot", record["lot_id"]),
        ("7. Supplier", record["supplier_id"]),
    ]

    for title, value in stages:
        display_value = (
            str(value) if pd.notna(value) and value
            else "Missing relationship"
        )
        st.markdown(f"**{title}**")
        st.code(display_value)

    st.divider()

    st.subheader("Inspection Details")
    st.json({
        "inspection_id": str(record["inspection_id"]),
        "inspection_date": str(record["inspected_at"]),
        "inspected_quantity": int(record["inspected_quantity"]),
        "defective_quantity": int(record["defective_quantity"]),
        "result": str(record["inspection_result"]),
    })

    st.subheader("Product and Production")
    st.dataframe(
        pd.DataFrame([{
            "SKU": record["sku"],
            "Product": record["product_name"],
            "Category": record["category"],
            "Order": record["order_id"],
            "Planned Quantity": record["planned_quantity"],
            "Order Status": record["order_status"],
            "Start Date": record["start_date"],
        }]),
        width="stretch",
        hide_index=True,
    )

    st.subheader("Process and Machine")
    st.dataframe(
        pd.DataFrame([{
            "Step": record["step_id"],
            "Process": record["process_name"],
            "Machine": record["machine_name"],
            "Temperature": record["temperature"],
            "Pressure": record["pressure"],
            "Process Status": record["process_status"],
        }]),
        width="stretch",
        hide_index=True,
    )

    st.subheader("Material Lot and Supplier")

    if pd.notna(record["lot_id"]):
        st.dataframe(
            pd.DataFrame([{
                "Lot ID": record["lot_id"],
                "Material": record["material_code"],
                "Received": record["received_date"],
                "Supplier": record["supplier_name"],
                "Country": record["country"],
                "Risk Tier": record["risk_tier"],
            }]),
            width="stretch",
            hide_index=True,
        )
    else:
        st.warning("This defect has no linked material lot.")

    st.subheader("Other Orders Using the Same Material Lot")

    if pd.notna(record["lot_id"]):
        affected_orders = read_query("""
            SELECT DISTINCT
                po.order_id,
                p.name AS product_name,
                po.planned_quantity,
                po.status
            FROM material_consumption mc
            JOIN production_orders po
                ON po.order_id = mc.order_id
            JOIN products p
                ON p.sku = po.sku
            WHERE mc.lot_id = ?
            ORDER BY po.order_id
        """, (record["lot_id"],))

        st.dataframe(
            affected_orders,
            width="stretch",
            hide_index=True,
        )


elif page == "Production Investigation":

    st.header("Production Order Investigation")

    orders = read_query("""
        SELECT order_id
        FROM production_orders
        ORDER BY order_id
    """)

    if orders.empty:
        st.warning("No production orders available.")
        st.stop()

    order_id = st.selectbox(
        "Select Production Order",
        orders["order_id"].tolist(),
    )

    order = read_query("""
        SELECT
            po.*,
            p.name AS product_name,
            p.category
        FROM production_orders po
        JOIN products p ON p.sku = po.sku
        WHERE po.order_id = ?
    """, (order_id,))

    if order.empty:
        st.error("Production order not found.")
        st.stop()

    order = order.iloc[0]

    a, b, c, d = st.columns(4)
    a.metric("Order ID", order_id)
    b.metric("Product", order["product_name"])
    c.metric("Planned Quantity", int(order["planned_quantity"]))
    d.metric("Status", order["status"])

    st.divider()

    st.subheader("Bill of Materials")

    bom = read_query("""
        SELECT
            b.material_code,
            b.quantity_per_unit,
            b.effective_from,
            b.effective_to
        FROM bom b
        WHERE b.sku = ?
          AND b.effective_from <= ?
          AND (b.effective_to IS NULL OR b.effective_to >= ?)
        ORDER BY b.material_code
    """, (order["sku"], order["start_date"], order["start_date"]))

    st.dataframe(bom, width="stretch", hide_index=True)

    st.subheader("Consumed Materials and Supplier Lots")

    consumption = read_query("""
        SELECT
            mc.material_code,
            mc.quantity_used,
            ml.lot_id,
            ml.received_date,
            s.supplier_id,
            s.name AS supplier_name,
            s.country,
            s.risk_tier
        FROM material_consumption mc
        JOIN material_lots ml ON ml.lot_id = mc.lot_id
        JOIN suppliers s ON s.supplier_id = ml.supplier_id
        WHERE mc.order_id = ?
        ORDER BY mc.material_code
    """, (order_id,))

    st.dataframe(
        consumption,
        width="stretch",
        hide_index=True,
    )

    st.subheader("Manufacturing Process Steps")

    steps = read_query("""
        SELECT
            ps.step_number,
            ps.step_id,
            ps.process_name,
            m.machine_name,
            m.machine_id,
            ps.temperature,
            ps.pressure,
            ps.started_at,
            ps.completed_at,
            ps.status
        FROM process_steps ps
        JOIN machines m ON m.machine_id = ps.machine_id
        WHERE ps.order_id = ?
        ORDER BY ps.step_number
    """, (order_id,))

    st.dataframe(steps, width="stretch", hide_index=True)

    st.subheader("Inspection History")

    inspections = read_query("""
        SELECT
            ir.inspection_id,
            ir.inspected_at,
            ip.inspection_stage,
            ir.inspected_quantity,
            ir.defective_quantity,
            ir.result
        FROM inspection_results ir
        JOIN inspection_plans ip ON ip.plan_id = ir.plan_id
        WHERE ir.order_id = ?
        ORDER BY ir.inspected_at
    """, (order_id,))

    st.dataframe(
        inspections,
        width="stretch",
        hide_index=True,
    )

    st.subheader("Defects Linked to This Order")

    order_defects = read_query("""
        SELECT
            defect_id,
            defect_type,
            severity,
            affected_quantity,
            disposition
        FROM defects
        WHERE order_id = ?
    """, (order_id,))

    st.dataframe(
        order_defects,
        width="stretch",
        hide_index=True,
    )


elif page == "Supplier Quality":

    st.header("Supplier Quality Intelligence")

    supplier_data = read_query("""
        WITH lot_summary AS (
            SELECT
                supplier_id,
                COUNT(*) AS total_lots,
                SUM(quantity_received) AS quantity_received
            FROM material_lots
            GROUP BY supplier_id
        ),
        defect_summary AS (
            SELECT
                ml.supplier_id,
                COUNT(DISTINCT d.defect_id) AS defect_count,
                SUM(d.affected_quantity) AS affected_units
            FROM defects d
            JOIN material_lots ml ON ml.lot_id = d.lot_id
            GROUP BY ml.supplier_id
        )
        SELECT
            s.supplier_id,
            s.name,
            s.country,
            s.risk_tier,
            s.active,
            COALESCE(ls.total_lots, 0) AS total_lots,
            COALESCE(ls.quantity_received, 0) AS quantity_received,
            COALESCE(ds.defect_count, 0) AS defect_count,
            COALESCE(ds.affected_units, 0) AS affected_units
        FROM suppliers s
        LEFT JOIN lot_summary ls
            ON ls.supplier_id = s.supplier_id
        LEFT JOIN defect_summary ds
            ON ds.supplier_id = s.supplier_id
        ORDER BY defect_count DESC, s.name
    """)

    if not supplier_data.empty:
        total_supplier_defects = supplier_data["defect_count"].sum()
        supplier_count = len(supplier_data)
        high_risk = len(
            supplier_data[supplier_data["risk_tier"] == "HIGH"]
        )

        a, b, c = st.columns(3)
        a.metric("Total Suppliers", supplier_count)
        b.metric("High-Risk Suppliers", high_risk)
        c.metric("Supplier-Linked Defects", int(total_supplier_defects))

        st.divider()

        st.subheader("Supplier Quality Scorecard")

        st.dataframe(
            supplier_data,
            width="stretch",
            hide_index=True,
        )

        st.subheader("Defects by Supplier")

        fig = px.bar(
            supplier_data.sort_values(
                "defect_count", ascending=False
            ),
            x="name",
            y="defect_count",
            color="risk_tier",
            hover_data=["country", "total_lots", "affected_units"],
            title="Supplier-Linked Defect Counts",
        )
        st.plotly_chart(fig, width="stretch")

        st.subheader("Supplier Risk Distribution")

        risk = (
            supplier_data.groupby("risk_tier")
            .size()
            .reset_index(name="suppliers")
        )

        fig = px.pie(
            risk,
            names="risk_tier",
            values="suppliers",
            hole=0.5,
        )
        st.plotly_chart(fig, width="stretch")

        st.caption(
            "Supplier-linked defects are attributed through the "
            "material lot recorded on each defect. Defects without "
            "a lot reference are not included in this attribution."
        )


elif page == "CAPA Management":

    st.header("Corrective and Preventive Action Management")

    capa_data = read_query("""
        SELECT
            ca.capa_id,
            ca.title,
            ca.root_cause,
            ca.status,
            ca.opened_date,
            ca.implemented_date,
            ca.verified_date,
            ca.closed_date,
            d.defect_id,
            d.defect_type,
            d.severity,
            d.order_id,
            d.affected_quantity
        FROM corrective_actions ca
        JOIN defects d ON d.defect_id = ca.defect_id
        ORDER BY ca.opened_date DESC
    """)

    if capa_data.empty:
        st.info("No corrective actions are available.")
        st.stop()

    total = len(capa_data)
    closed = len(capa_data[capa_data["status"] == "CLOSED"])
    open_count = total - closed
    verified = len(capa_data[capa_data["status"] == "VERIFIED"])

    a, b, c, d = st.columns(4)
    a.metric("Total CAPAs", total)
    b.metric("Open CAPAs", open_count)
    c.metric("Verified CAPAs", verified)
    d.metric("Closed CAPAs", closed)

    st.divider()

    st.subheader("CAPA Lifecycle Distribution")

    status_counts = (
        capa_data.groupby("status")
        .size()
        .reset_index(name="total")
    )

    fig = px.pie(
        status_counts,
        names="status",
        values="total",
        hole=0.5,
    )

    st.plotly_chart(fig, width="stretch")

    st.subheader("Corrective Action Register")

    st.dataframe(
        capa_data,
        width="stretch",
        hide_index=True,
    )

    capa_ids = capa_data["capa_id"].tolist()

    selected_capa = st.selectbox(
        "Investigate CAPA",
        capa_ids,
    )

    selected = capa_data[
        capa_data["capa_id"] == selected_capa
    ].iloc[0]

    st.subheader("CAPA Investigation")

    st.write(f"**CAPA:** {selected['capa_id']}")
    st.write(f"**Title:** {selected['title']}")
    st.write(f"**Root Cause:** {selected['root_cause']}")
    st.write(f"**Linked Defect:** {selected['defect_id']}")
    st.write(f"**Defect Severity:** {selected['severity']}")
    st.write(f"**Production Order:** {selected['order_id']}")
    st.write(f"**Current Status:** {selected['status']}")

    st.subheader("Lifecycle Dates")

    timeline = pd.DataFrame([
        {"Stage": "Opened", "Date": selected["opened_date"]},
        {"Stage": "Implemented", "Date": selected["implemented_date"]},
        {"Stage": "Verified", "Date": selected["verified_date"]},
        {"Stage": "Closed", "Date": selected["closed_date"]},
    ])

    st.dataframe(
        timeline,
        width="stretch",
        hide_index=True,
    )

    st.caption(
        "This dashboard provides read-only CAPA monitoring. "
        "Workflow transitions and audit logging are handled "
        "separately by the CAPA service."
    )


elif page == "TraceForge Copilot":

    st.header("TraceForge Copilot")
    st.write(
        "Investigate manufacturing defects using database-grounded "
        "evidence and locally hosted AI explanations."
    )

    st.info(
        "Copilot retrieves evidence from the TraceForge SQLite database. "
        "Ollama generates explanations locally."
    )

    with st.form("copilot_investigation_form"):

        question = st.text_area(
            "Investigation Question",
            value="Investigate defect DEF-2026-000001",
            height=100,
            placeholder=(
                "Example: Investigate DEF-2026-000001"
            ),
        )

        model = st.selectbox(
            "Local AI Model",
            [
                "llama3.2:3b",
                "llama3.1:8b",
                "llama3:8b",
                "llama3:latest",
                "mistral:latest",
                "gemma:2b",
            ],
            index=0,
        )

        submitted = st.form_submit_button(
            "Run Investigation",
            type="primary",
            width="stretch",
        )

    if submitted:

        if not question.strip():
            st.warning("Enter an investigation question.")

        else:

            try:
                with st.spinner(
                    "Retrieving manufacturing evidence..."
                ):
                    result = retrieve_evidence(
                        DB_PATH,
                        question,
                    )

                st.success("Database evidence retrieved.")

                st.subheader("Investigation Overview")

                a, b, c = st.columns(3)

                a.metric(
                    "Investigation Type",
                    result["investigation_type"].replace("_", " ").title(),
                )

                b.metric(
                    "Matched Identifiers",
                    len(result["matched_ids"]),
                )

                c.metric(
                    "Source References",
                    len(result["source_references"]),
                )

                if result["matched_ids"]:
                    st.write("**Matched IDs**")
                    st.json(result["matched_ids"])

                with st.expander(
                    "View Retrieved Database Evidence",
                    expanded=True,
                ):
                    st.json(result["evidence"])

                if result["source_references"]:
                    with st.expander("Source Record References"):
                        st.code(
                            "\n".join(result["source_references"])
                        )

                st.divider()
                st.subheader("AI Investigation Report")

                try:
                    with st.spinner(
                        f"Generating explanation with {model}..."
                    ):
                        answer = answer_with_ollama(
                            result,
                            model=model,
                        )

                    st.markdown(answer)

                except Exception as exc:
                    st.error(
                        f"AI explanation unavailable: {exc}"
                    )
                    st.warning(
                        "Database evidence was retrieved successfully. "
                        "You can still inspect the evidence above."
                    )

            except Exception as exc:
                st.error(f"Investigation failed: {exc}")


st.sidebar.divider()
st.sidebar.caption("TraceForge AI | Quality & Traceability")
st.sidebar.caption("Prototype demonstration build")

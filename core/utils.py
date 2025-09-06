# core/utils.py

import graphviz
from django.utils.html import mark_safe
import textwrap

def _post_process_svg(svg_code):
    """SVG را برای نمایش در HTML تمیز می‌کند."""
    processed_svg = svg_code.replace('<?xml version="1.0" encoding="UTF-8" standalone="no"?>', '')
    processed_svg = processed_svg.replace('width=', 'class="graph-svg" width=')
    return mark_safe(processed_svg)

def generate_process_graph(process, highlighted_step_id=None):
    """
    یک گراف SVG با لیبل‌های HTML-Like برای مراحل یک فرایند ایجاد می‌کند تا از بیرون‌زدگی متن جلوگیری شود.
    """
    try:
        dot = graphviz.Digraph(comment=process.name)
        dot.attr('node', shape='box', style='rounded,filled', fontname='Vazirmatn')
        dot.attr('edge', fontname='Vazirmatn')
        dot.attr(rankdir='TB', splines='ortho')
        
        dot.graph_attr['class'] = 'graph-bg'
        dot.node_attr['class'] = 'graph-node'
        dot.edge_attr['class'] = 'graph-edge'
        
        steps = process.steps.order_by('step_order')
        if not steps:
            return ""

        dot.node('start', 'شروع', shape='ellipse', **{'class': 'graph-node start'})
        dot.edge('start', str(steps.first().id))

        for step in steps:
            node_class = 'graph-node'
            if step.id == highlighted_step_id:
                node_class += ' highlighted'
            
            # ===== تغییر کلیدی: استفاده از لیبل‌های HTML-Like برای کنترل کامل =====
            
            # 1. شکستن متن نام مرحله به خطوط کوتاه‌تر
            wrapped_name = textwrap.fill(step.name, width=25).replace('\n', '<BR/>')
            
            # 2. تعیین رشته مربوط به مسئول
            responsible_person_str = ""
            if step.default_responsible_user:
                responsible_person_str = (
                    step.default_responsible_user.get_full_name() or
                    step.default_responsible_user.username
                )
            else:
                responsible_person_str = "مدیر مستقیم"

            # 3. ساخت ساختار جدول HTML-Like
            node_label = f'''<
<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="4">
  <TR><TD ALIGN="CENTER">{wrapped_name}</TD></TR>
  <TR><TD ALIGN="CENTER"><FONT POINT-SIZE="10" COLOR="#555555">({responsible_person_str})</FONT></TD></TR>
</TABLE>
>'''
            # ===================================================================
            
            dot.node(str(step.id), node_label, **{'class': node_class})

        for i in range(len(steps) - 1):
            dot.edge(str(steps[i].id), str(steps[i+1].id))
        
        dot.node('end', 'پایان', shape='ellipse', **{'class': 'graph-node end'})
        dot.edge(str(steps.last().id), 'end')

        svg_code = dot.pipe(format='svg').decode('utf-8')
        return _post_process_svg(svg_code)

    except Exception as e:
        print(f"Error generating graph: {e}")
        return "خطا در تولید گراف."

def generate_org_chart_graph(root_users):
    """
    یک گراف SVG با کلاس‌های CSS برای چارت سازمانی ایجاد می‌کند.
    """
    try:
        dot = graphviz.Digraph('OrgChart')
        dot.attr('node', shape='box', style='rounded,filled', fontname='Vazirmatn')
        dot.attr(rankdir='TB', splines='ortho')
        
        dot.graph_attr['class'] = 'graph-bg'
        dot.node_attr['class'] = 'graph-node'
        dot.edge_attr['class'] = 'graph-edge'
        
        all_users = set()
        
        def add_user_and_subordinates(user):
            if user.id in all_users: return
            
            user_label = f"{user.get_full_name() or user.username}\n<FONT POINT-SIZE=\"10\">{user.groups.first().name if user.groups.exists() else 'کاربر'}</FONT>"
            dot.node(str(user.id), f"<{user_label}>")
            all_users.add(user.id)
            
            for subordinate in user.subordinates.all():
                dot.edge(str(user.id), str(subordinate.id))
                add_user_and_subordinates(subordinate)

        for user in root_users:
            add_user_and_subordinates(user)

        if not all_users:
            return "هیچ کاربری برای نمایش در چارت سازمانی یافت نشد."

        svg_code = dot.pipe(format='svg').decode('utf-8')
        return _post_process_svg(svg_code)

    except Exception as e:
        print(f"Error generating org chart graph: {e}")
        return "خطا در تولید گراف چارت سازمانی."
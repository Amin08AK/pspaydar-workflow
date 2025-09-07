# core/utils.py

import graphviz
from django.utils.html import mark_safe
import textwrap
import arabic_reshaper

def _fix_persian_text_shape(text):
    if not text:
        return ""
    reshaped_text = arabic_reshaper.reshape(text)
    return reshaped_text

def _post_process_svg(svg_code):
    processed_svg = svg_code.replace('<?xml version="1.0" encoding="UTF-8" standalone="no"?>', '')
    processed_svg = svg_code.replace('width=', 'class="graph-svg" width=')
    return mark_safe(processed_svg)

def generate_process_graph(process, highlighted_step_id=None):
    """
    نسخه نهایی: استفاده از جدول HTML با تراز افقی و عمودی مشخص برای بهترین نتیجه.
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

        dot.node('start', _fix_persian_text_shape('شروع'), shape='ellipse', **{'class': 'graph-node start'})
        dot.edge('start', str(steps.first().id))

        for step in steps:
            node_class = 'graph-node'
            if step.id == highlighted_step_id:
                node_class += ' highlighted'
            
            wrapped_name = textwrap.fill(step.name, width=25).split('\n')
            processed_wrapped_name = '<BR/>'.join([_fix_persian_text_shape(line) for line in wrapped_name])
            
            responsible_person_str = ""
            if step.default_responsible_user:
                responsible_person_str = (
                    step.default_responsible_user.get_full_name() or
                    step.default_responsible_user.username
                )
            else:
                responsible_person_str = "مدیر مستقیم"
            
            processed_responsible_str = _fix_persian_text_shape(f"({responsible_person_str})")

            node_label = f'''<
<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0">
  <TR>
    <TD ALIGN="CENTER" VALIGN="MIDDLE">
      {processed_wrapped_name}
      <BR/>
      <FONT POINT-SIZE="10" COLOR="#555555">{processed_responsible_str}</FONT>
    </TD>
  </TR>
</TABLE>
>'''
            
            dot.node(str(step.id), node_label, **{'class': node_class})

        for i in range(len(steps) - 1):
            dot.edge(str(steps[i].id), str(steps[i+1].id))
        
        dot.node('end', _fix_persian_text_shape('پایان'), shape='ellipse', **{'class': 'graph-node end'})
        dot.edge(str(steps.last().id), 'end')

        svg_code = dot.pipe(format='svg').decode('utf-8')
        return _post_process_svg(svg_code)

    except Exception as e:
        print(f"Error generating graph: {e}")
        return _fix_persian_text_shape("خطا در تولید گراف.")

def generate_org_chart_graph(root_users):
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
            
            full_name = _fix_persian_text_shape(user.get_full_name() or user.username)
            group_name = _fix_persian_text_shape(user.groups.first().name if user.groups.exists() else 'کاربر')

            user_label = f'''<
<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0">
    <TR><TD ALIGN="CENTER" VALIGN="MIDDLE">
    {full_name}<BR/><FONT POINT-SIZE="10">{group_name}</FONT>
    </TD></TR>
</TABLE>>'''
            
            dot.node(str(user.id), user_label)
            all_users.add(user.id)
            
            for subordinate in user.subordinates.all():
                dot.edge(str(user.id), str(subordinate.id))
                add_user_and_subordinates(subordinate)

        for user in root_users:
            add_user_and_subordinates(user)

        if not all_users:
            return _fix_persian_text_shape("هیچ کاربری برای نمایش در چارت سازمانی یافت نشد.")

        svg_code = dot.pipe(format='svg').decode('utf-8')
        return _post_process_svg(svg_code)

    except Exception as e:
        print(f"Error generating org chart graph: {e}")
        return _fix_persian_text_shape("خطا در تولید گراف چارت سازمانی.")
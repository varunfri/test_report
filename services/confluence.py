import pandas as pd
import html
from typing import List

class ConfluenceGenerator:
    @staticmethod
    def generate_html_table(df_subset: pd.DataFrame) -> str:
        """
        Generate a clean HTML table for a subset of data.
        """
        if df_subset.empty:
            return "<p>No test cases found.</p>"
            
        html_out = [
            '<table border="1" style="border-collapse: collapse; width: 100%; font-family: Segoe UI, sans-serif; font-size: 13px; border-color: #CBD5E1;">',
            '  <thead>',
            '    <tr style="background-color: #F8FAFC; color: #1E293B; font-weight: bold; text-align: left;">',
            '      <th style="padding: 8px;">Testcase ID</th>',
            '      <th style="padding: 8px;">Models</th>',
            '      <th style="padding: 8px;">Function</th>',
            '      <th style="padding: 8px;">Tester</th>',
            '      <th style="padding: 8px;">Comment</th>',
            '    </tr>',
            '  </thead>',
            '  <tbody>'
        ]
        
        for idx, row in df_subset.iterrows():
            tc_id = html.escape(str(row.get("Testcase ID", "")))
            models = html.escape(str(row.get("Models", "")))
            func = html.escape(str(row.get("Function", "")))
            tester = html.escape(str(row.get("Tester", "")))
            comment = html.escape(str(row.get("Comment", "")))
            
            html_out.append(f'    <tr>')
            html_out.append(f'      <td style="padding: 8px; font-weight: 500; color: #0F172A;">{tc_id}</td>')
            html_out.append(f'      <td style="padding: 8px; color: #475569;">{models}</td>')
            html_out.append(f'      <td style="padding: 8px; color: #475569;">{func}</td>')
            html_out.append(f'      <td style="padding: 8px; color: #475569;">{tester}</td>')
            html_out.append(f'      <td style="padding: 8px; color: #475569;">{comment}</td>')
            html_out.append(f'    </tr>')
            
        html_out.append('  </tbody>')
        html_out.append('</table>')
        return "\n".join(html_out)

    @classmethod
    def generate_confluence_xml(cls, df: pd.DataFrame) -> str:
        """
        Generate Confluence Storage Format (XHTML) utilizing deck, card, and expand macros.
        """
        if df.empty:
            return "<p>No data available for export.</p>"
            
        xml_out = [
            '<!-- Confluence Storage Format (XHTML) for Composition Deck Macro -->',
            '<ac:structured-macro ac:name="deck">',
            '  <ac:rich-text-body>'
        ]
        
        # 1. NA Card
        xml_out.append('    <ac:structured-macro ac:name="card">')
        xml_out.append('      <ac:parameter ac:name="label">NA</ac:parameter>')
        xml_out.append('      <ac:rich-text-body>')
        
        df_na = df[df["Testcase Status"] == "NA"]
        if df_na.empty:
            xml_out.append('        <p>No NA test cases found.</p>')
        else:
            # Group NA by region
            for region in sorted(df_na["Region"].unique()):
                df_reg_na = df_na[df_na["Region"] == region]
                xml_out.append('        <ac:structured-macro ac:name="expand">')
                xml_out.append(f'          <ac:parameter ac:name="title">Expand ({region} Region)</ac:parameter>')
                xml_out.append('          <ac:rich-text-body>')
                xml_out.append(cls.generate_html_table(df_reg_na))
                xml_out.append('          </ac:rich-text-body>')
                xml_out.append('        </ac:structured-macro>')
                
        xml_out.append('      </ac:rich-text-body>')
        xml_out.append('    </ac:structured-macro>')

        # 2. Blocked Card
        xml_out.append('    <ac:structured-macro ac:name="card">')
        xml_out.append('      <ac:parameter ac:name="label">Blocked</ac:parameter>')
        xml_out.append('      <ac:rich-text-body>')
        
        df_blocked = df[df["Testcase Status"] == "Blocked"]
        if df_blocked.empty:
            xml_out.append('        <p>No Blocked test cases found.</p>')
        else:
            # Group Blocked by region
            for region in sorted(df_blocked["Region"].unique()):
                df_reg_bl = df_blocked[df_blocked["Region"] == region]
                xml_out.append('        <ac:structured-macro ac:name="expand">')
                xml_out.append(f'          <ac:parameter ac:name="title">Expand ({region} Region)</ac:parameter>')
                xml_out.append('          <ac:rich-text-body>')
                xml_out.append(cls.generate_html_table(df_reg_bl))
                xml_out.append('          </ac:rich-text-body>')
                xml_out.append('        </ac:structured-macro>')
                
        xml_out.append('      </ac:rich-text-body>')
        xml_out.append('    </ac:structured-macro>')
        
        xml_out.append('  </ac:rich-text-body>')
        xml_out.append('</ac:structured-macro>')
        
        return "\n".join(xml_out)

    @classmethod
    def generate_pure_html(cls, df: pd.DataFrame) -> str:
        """
        Generate pure HTML layout using details/summary tags for standard browser paste fallback.
        """
        if df.empty:
            return "<p>No data available.</p>"
            
        html_out = [
            '<div style="font-family: Segoe UI, sans-serif; color: #1E293B;">',
            '  <h2 style="border-bottom: 2px solid #E2E8F0; padding-bottom: 8px;">Regional Test Case Overview</h2>'
        ]
        
        # Tabs container styling (simulating Deck)
        for label in ["NA", "Blocked"]:
            df_label = df[df["Testcase Status"] == label]
            
            html_out.append(f'  <div style="margin-bottom: 24px; padding: 16px; border: 1px solid #E2E8F0; border-radius: 8px; background-color: #FAFAFA;">')
            html_out.append(f'    <h3 style="margin-top: 0; color: #0F172A;">🏷️ Status: {label}</h3>')
            
            if df_label.empty:
                html_out.append(f'    <p style="color: #64748B;">No test cases with status {label}.</p>')
            else:
                for region in sorted(df_label["Region"].unique()):
                    df_reg = df_label[df_label["Region"] == region]
                    html_out.append(f'    <details style="margin-bottom: 12px; background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 4px; padding: 10px;">')
                    html_out.append(f'      <summary style="font-weight: 600; cursor: pointer; color: #1E40AF; outline: none;">Expand ({region} Region)</summary>')
                    html_out.append(f'      <div style="margin-top: 8px;">')
                    html_out.append(cls.generate_html_table(df_reg))
                    html_out.append(f'      </div>')
                    html_out.append(f'    </details>')
            html_out.append(f'  </div>')
            
        html_out.append('</div>')
        return "\n".join(html_out)

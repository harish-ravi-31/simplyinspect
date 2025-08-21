"""
SharePoint Permissions PDF Report Service

Generates comprehensive PDF reports for SharePoint permissions analysis.
"""

import io
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    PageBreak, Image, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.legends import Legend
from reportlab.lib.colors import HexColor
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
from io import BytesIO
import base64

logger = logging.getLogger(__name__)

class PermissionReportService:
    """Service for generating PDF reports of SharePoint permissions"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        
    def _setup_custom_styles(self):
        """Setup custom paragraph styles for the report"""
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Title'],
            fontSize=24,
            textColor=HexColor('#1976D2'),
            spaceAfter=30,
            alignment=TA_CENTER
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionTitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            textColor=HexColor('#424242'),
            spaceAfter=12,
            spaceBefore=12
        ))
        
        self.styles.add(ParagraphStyle(
            name='MetricValue',
            parent=self.styles['Normal'],
            fontSize=14,
            textColor=HexColor('#1976D2'),
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
    async def generate_permissions_report(
        self,
        permissions_data: List[Dict[str, Any]],
        site_filter: Optional[str] = None,
        person_filter: Optional[str] = None,
        permission_type_filter: Optional[str] = None,
        include_charts: bool = True
    ) -> bytes:
        """
        Generate a comprehensive PDF report of SharePoint permissions
        
        Args:
            permissions_data: List of permission records
            site_filter: Optional site ID filter
            person_filter: Optional person email filter
            permission_type_filter: Optional permission type filter
            include_charts: Whether to include visual charts
            
        Returns:
            PDF file as bytes
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18,
        )
        
        story = []
        
        # Title Page
        story.append(Paragraph("SharePoint Permissions Report", self.styles['CustomTitle']))
        story.append(Spacer(1, 12))
        
        # Report metadata
        metadata = self._create_metadata_section(
            permissions_data, site_filter, person_filter, permission_type_filter
        )
        story.extend(metadata)
        
        # Executive Summary
        story.append(PageBreak())
        story.append(Paragraph("Executive Summary", self.styles['SectionTitle']))
        summary = self._create_executive_summary(permissions_data)
        story.extend(summary)
        
        # Statistics with charts
        if include_charts:
            story.append(PageBreak())
            story.append(Paragraph("Permission Statistics", self.styles['SectionTitle']))
            charts = self._create_permission_charts(permissions_data)
            story.extend(charts)
        
        # Detailed Permissions by Site
        story.append(PageBreak())
        story.append(Paragraph("Detailed Permissions by Site", self.styles['SectionTitle']))
        detailed = self._create_detailed_permissions_section(permissions_data)
        story.extend(detailed)
        
        # Users and Groups Summary
        story.append(PageBreak())
        story.append(Paragraph("Users and Groups Summary", self.styles['SectionTitle']))
        users_groups = self._create_users_groups_section(permissions_data)
        story.extend(users_groups)
        
        # Unique Permissions Analysis
        story.append(PageBreak())
        story.append(Paragraph("Unique Permissions Analysis", self.styles['SectionTitle']))
        unique_perms = self._create_unique_permissions_section(permissions_data)
        story.extend(unique_perms)
        
        # Build PDF
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes
    
    def _create_metadata_section(
        self,
        permissions_data: List[Dict[str, Any]],
        site_filter: Optional[str],
        person_filter: Optional[str],
        permission_type_filter: Optional[str]
    ) -> List:
        """Create report metadata section"""
        elements = []
        
        # Report generation info
        metadata_table_data = [
            ["Report Generated:", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
            ["Total Records:", str(len(permissions_data))],
        ]
        
        if site_filter:
            metadata_table_data.append(["Site Filter:", site_filter])
        if person_filter:
            metadata_table_data.append(["Person Filter:", person_filter])
        if permission_type_filter:
            metadata_table_data.append(["Permission Type Filter:", permission_type_filter])
        
        metadata_table = Table(metadata_table_data, colWidths=[2*inch, 4*inch])
        metadata_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ]))
        
        elements.append(metadata_table)
        elements.append(Spacer(1, 20))
        
        return elements
    
    def _create_executive_summary(self, permissions_data: List[Dict[str, Any]]) -> List:
        """Create executive summary section"""
        elements = []
        
        # Calculate summary statistics
        unique_sites = len(set(p.get('site_id', '') for p in permissions_data))
        unique_users = len(set(p.get('principal_email', '') for p in permissions_data if p.get('principal_type') == 'User'))
        unique_groups = len(set(p.get('principal_id', '') for p in permissions_data if p.get('principal_type') == 'Group'))
        unique_resources = len(set(p.get('resource_id', '') for p in permissions_data))
        
        # Permissions with broken inheritance
        broken_inheritance = len([p for p in permissions_data if p.get('has_broken_inheritance', False)])
        
        # Create summary cards
        summary_data = [
            ["Sites", "Users", "Groups", "Resources"],
            [str(unique_sites), str(unique_users), str(unique_groups), str(unique_resources)]
        ]
        
        summary_table = Table(summary_data, colWidths=[1.5*inch]*4)
        summary_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#E3F2FD')),
            ('TEXTCOLOR', (0, 1), (-1, 1), HexColor('#1976D2')),
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (-1, 1), 16),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white]),
        ]))
        
        elements.append(summary_table)
        elements.append(Spacer(1, 20))
        
        # Key findings
        findings = []
        findings.append(Paragraph("<b>Key Findings:</b>", self.styles['Heading3']))
        findings.append(Spacer(1, 10))
        
        if broken_inheritance > 0:
            findings.append(Paragraph(
                f"• {broken_inheritance} resources have broken permission inheritance",
                self.styles['Normal']
            ))
        
        # Permission level distribution
        permission_levels = {}
        for p in permissions_data:
            level = p.get('permission_level', 'Unknown')
            permission_levels[level] = permission_levels.get(level, 0) + 1
        
        most_common_permission = max(permission_levels.items(), key=lambda x: x[1])
        findings.append(Paragraph(
            f"• Most common permission level: {most_common_permission[0]} ({most_common_permission[1]} instances)",
            self.styles['Normal']
        ))
        
        elements.extend(findings)
        
        return elements
    
    def _create_permission_charts(self, permissions_data: List[Dict[str, Any]]) -> List:
        """Create visual charts for permission statistics"""
        elements = []
        
        # Permission Type Distribution Pie Chart
        permission_types = {}
        for p in permissions_data:
            ptype = p.get('permission_type', 'Unknown')
            permission_types[ptype] = permission_types.get(ptype, 0) + 1
        
        if permission_types:
            # Create matplotlib pie chart
            fig, ax = plt.subplots(figsize=(6, 4))
            ax.pie(
                permission_types.values(),
                labels=permission_types.keys(),
                autopct='%1.1f%%',
                startangle=90
            )
            ax.set_title('Permission Type Distribution')
            
            # Save to bytes
            img_buffer = BytesIO()
            plt.savefig(img_buffer, format='png', bbox_inches='tight', dpi=100)
            img_buffer.seek(0)
            plt.close()
            
            # Add to story
            img = Image(img_buffer, width=4*inch, height=2.5*inch)
            elements.append(img)
            elements.append(Spacer(1, 20))
        
        # Permission Levels Bar Chart
        permission_levels = {}
        for p in permissions_data:
            level = p.get('permission_level', 'Unknown')
            permission_levels[level] = permission_levels.get(level, 0) + 1
        
        if permission_levels:
            # Create bar chart
            fig, ax = plt.subplots(figsize=(8, 4))
            levels = list(permission_levels.keys())
            counts = list(permission_levels.values())
            
            ax.bar(levels, counts, color='#1976D2')
            ax.set_xlabel('Permission Level')
            ax.set_ylabel('Count')
            ax.set_title('Permission Levels Distribution')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            
            # Save to bytes
            img_buffer = BytesIO()
            plt.savefig(img_buffer, format='png', bbox_inches='tight', dpi=100)
            img_buffer.seek(0)
            plt.close()
            
            # Add to story
            img = Image(img_buffer, width=5*inch, height=2.5*inch)
            elements.append(img)
        
        return elements
    
    def _create_detailed_permissions_section(self, permissions_data: List[Dict[str, Any]]) -> List:
        """Create detailed permissions breakdown by site"""
        elements = []
        
        # Group permissions by site
        sites = {}
        for p in permissions_data:
            site_url = p.get('site_url', 'Unknown')
            if site_url not in sites:
                sites[site_url] = []
            sites[site_url].append(p)
        
        # Create table for each site (limit to first 5 for brevity)
        for i, (site_url, site_perms) in enumerate(list(sites.items())[:5]):
            if i > 0:
                elements.append(Spacer(1, 20))
            
            elements.append(Paragraph(f"<b>Site:</b> {site_url}", self.styles['Heading3']))
            elements.append(Spacer(1, 10))
            
            # Create permissions table
            table_data = [['Resource', 'Principal', 'Permission Level', 'Type']]
            
            for perm in site_perms[:20]:  # Limit to 20 entries per site
                table_data.append([
                    perm.get('resource_name', '')[:30],  # Truncate long names
                    perm.get('principal_name', '')[:30],
                    perm.get('permission_level', ''),
                    perm.get('principal_type', '')
                ])
            
            if len(site_perms) > 20:
                table_data.append(['...', '...', '...', '...'])
                table_data.append([f'Total: {len(site_perms)} permissions', '', '', ''])
            
            perm_table = Table(table_data, colWidths=[2*inch, 2*inch, 1.5*inch, 1*inch])
            perm_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (-1, 0), HexColor('#E3F2FD')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, HexColor('#F5F5F5')]),
            ]))
            
            elements.append(perm_table)
        
        if len(sites) > 5:
            elements.append(Spacer(1, 10))
            elements.append(Paragraph(
                f"<i>... and {len(sites) - 5} more sites</i>",
                self.styles['Normal']
            ))
        
        return elements
    
    def _create_users_groups_section(self, permissions_data: List[Dict[str, Any]]) -> List:
        """Create users and groups summary section"""
        elements = []
        
        # Collect user statistics
        users = {}
        groups = {}
        
        for p in permissions_data:
            if p.get('principal_type') == 'User':
                email = p.get('principal_email', p.get('principal_name', 'Unknown'))
                if email not in users:
                    users[email] = {
                        'name': p.get('principal_name', ''),
                        'permissions': []
                    }
                users[email]['permissions'].append({
                    'resource': p.get('resource_name', ''),
                    'level': p.get('permission_level', '')
                })
            elif p.get('principal_type') == 'Group':
                group_name = p.get('principal_name', 'Unknown')
                if group_name not in groups:
                    groups[group_name] = {
                        'id': p.get('principal_id', ''),
                        'permissions': []
                    }
                groups[group_name]['permissions'].append({
                    'resource': p.get('resource_name', ''),
                    'level': p.get('permission_level', '')
                })
        
        # Top users by permission count
        elements.append(Paragraph("<b>Top Users by Permission Count:</b>", self.styles['Heading3']))
        elements.append(Spacer(1, 10))
        
        user_table_data = [['User', 'Permission Count']]
        sorted_users = sorted(users.items(), key=lambda x: len(x[1]['permissions']), reverse=True)[:10]
        
        for email, user_data in sorted_users:
            user_table_data.append([email, str(len(user_data['permissions']))])
        
        user_table = Table(user_table_data, colWidths=[4*inch, 2*inch])
        user_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#E3F2FD')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, HexColor('#F5F5F5')]),
        ]))
        
        elements.append(user_table)
        elements.append(Spacer(1, 20))
        
        # Top groups
        elements.append(Paragraph("<b>Top Groups by Permission Count:</b>", self.styles['Heading3']))
        elements.append(Spacer(1, 10))
        
        group_table_data = [['Group', 'Permission Count']]
        sorted_groups = sorted(groups.items(), key=lambda x: len(x[1]['permissions']), reverse=True)[:10]
        
        for group_name, group_data in sorted_groups:
            group_table_data.append([group_name[:40], str(len(group_data['permissions']))])
        
        group_table = Table(group_table_data, colWidths=[4*inch, 2*inch])
        group_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#E3F2FD')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, HexColor('#F5F5F5')]),
        ]))
        
        elements.append(group_table)
        
        return elements
    
    def _create_unique_permissions_section(self, permissions_data: List[Dict[str, Any]]) -> List:
        """Create analysis of unique permissions"""
        elements = []
        
        # Resources with broken inheritance
        broken_inheritance = [p for p in permissions_data if p.get('has_broken_inheritance', False)]
        
        elements.append(Paragraph(
            f"<b>Resources with Unique Permissions: {len(set(p.get('resource_id') for p in broken_inheritance))}</b>",
            self.styles['Heading3']
        ))
        elements.append(Spacer(1, 10))
        
        if broken_inheritance:
            # Group by resource
            unique_resources = {}
            for p in broken_inheritance:
                resource_id = p.get('resource_id', '')
                if resource_id not in unique_resources:
                    unique_resources[resource_id] = {
                        'name': p.get('resource_name', ''),
                        'type': p.get('resource_type', ''),
                        'principals': []
                    }
                unique_resources[resource_id]['principals'].append(p.get('principal_name', ''))
            
            # Create table
            table_data = [['Resource', 'Type', 'Unique Principals']]
            
            for resource_id, resource_data in list(unique_resources.items())[:15]:
                table_data.append([
                    resource_data['name'][:40],
                    resource_data['type'],
                    str(len(set(resource_data['principals'])))
                ])
            
            unique_table = Table(table_data, colWidths=[3*inch, 1.5*inch, 1.5*inch])
            unique_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (2, 0), (2, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (-1, 0), HexColor('#FFE0B2')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, HexColor('#FFF8E1')]),
            ]))
            
            elements.append(unique_table)
            
            if len(unique_resources) > 15:
                elements.append(Spacer(1, 10))
                elements.append(Paragraph(
                    f"<i>... and {len(unique_resources) - 15} more resources with unique permissions</i>",
                    self.styles['Normal']
                ))
        else:
            elements.append(Paragraph(
                "No resources with broken permission inheritance found.",
                self.styles['Normal']
            ))
        
        return elements
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
from fpdf import FPDF
from .models import Activity, Report
from .db import db
import json

class ProductivityReport:
    def __init__(self, user, start_date, end_date):
        self.user = user
        self.start_date = start_date
        self.end_date = end_date
        self.activities = Activity.query.filter(
            Activity.user_id == user.id,
            Activity.start_time >= start_date,
            Activity.start_time <= end_date
        ).order_by(Activity.start_time).all()
        
    def generate_report(self, format='pdf'):
        if format == 'pdf':
            return self._generate_pdf()
        elif format == 'csv':
            return self._generate_csv()
        elif format == 'excel':
            return self._generate_excel()
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _prepare_data(self):
        data = []
        for activity in self.activities:
            duration = (activity.end_time - activity.start_time).total_seconds() / 3600 if activity.end_time else 0
            data.append({
                'Date': activity.start_time.date(),
                'Start Time': activity.start_time.strftime('%H:%M'),
                'End Time': activity.end_time.strftime('%H:%M') if activity.end_time else '',
                'Duration (hours)': round(duration, 2),
                'Activity Type': activity.activity_type,
                'Productivity Score': activity.productivity_score or 0,
                'Details': json.dumps(activity.details) if activity.details else ''
            })
        return pd.DataFrame(data)

    def _generate_pdf(self):
        df = self._prepare_data()
        
        # Create PDF
        pdf = FPDF()
        pdf.add_page()
        
        # Title
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, 'Your Project Title Here', 0, 1, 'C')
        
        # Report Info
        pdf.set_font('Arial', '', 12)
        pdf.cell(0, 10, f'User: {self.user.name}', 0, 1)
        pdf.cell(0, 10, f'Period: {self.start_date.strftime("%Y-%m-%d")} to {self.end_date.strftime("%Y-%m-%d")}', 0, 1)
        
        # Summary Statistics
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, 'Summary', 0, 1)
        pdf.set_font('Arial', '', 12)
        
        avg_productivity = df['Productivity Score'].mean()
        total_hours = df['Duration (hours)'].sum()
        
        pdf.cell(0, 10, f'Average Productivity: {avg_productivity:.1f}%', 0, 1)
        pdf.cell(0, 10, f'Total Hours: {total_hours:.1f}', 0, 1)
        
        # Create graphs
        self._add_productivity_graph(pdf)
        self._add_activity_breakdown(pdf)
        
        # Save the report
        filename = f'reports/productivity_report_{self.user.id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        os.makedirs('reports', exist_ok=True)
        print(f"Saving report to {filename}")
        pdf.output(filename)
        print("Report saved successfully.")
        
        # Create report record
        report = Report(
            user_id=self.user.id,
            report_type='productivity',
            start_date=self.start_date,
            end_date=self.end_date,
            format='pdf',
            file_path=filename
        )
        db.session.add(report)
        db.session.commit()
        
        return filename

    def _generate_csv(self):
        df = self._prepare_data()
        filename = f'reports/productivity_report_{self.user.id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        os.makedirs('reports', exist_ok=True)
        df.to_csv(filename, index=False)
        
        report = Report(
            user_id=self.user.id,
            report_type='productivity',
            start_date=self.start_date,
            end_date=self.end_date,
            format='csv',
            file_path=filename
        )
        db.session.add(report)
        db.session.commit()
        
        return filename

    def _generate_excel(self):
        df = self._prepare_data()
        filename = f'reports/productivity_report_{self.user.id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        os.makedirs('reports', exist_ok=True)
        
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Activity Data', index=False)
            
            # Create summary sheet
            summary_data = {
                'Metric': [
                    'Average Productivity',
                    'Total Hours',
                    'Number of Activities',
                    'Most Productive Day',
                    'Peak Productivity Hour'
                ],
                'Value': [
                    f"{df['Productivity Score'].mean():.1f}%",
                    f"{df['Duration (hours)'].sum():.1f}",
                    len(df),
                    df.groupby('Date')['Productivity Score'].mean().idxmax().strftime('%Y-%m-%d'),
                    df.groupby(pd.to_datetime(df['Start Time']).dt.hour)['Productivity Score'].mean().idxmax()
                ]
            }
            pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
        
        report = Report(
            user_id=self.user.id,
            report_type='productivity',
            start_date=self.start_date,
            end_date=self.end_date,
            format='excel',
            file_path=filename
        )
        db.session.add(report)
        db.session.commit()
        
        return filename

    def _add_productivity_graph(self, pdf):
        df = self._prepare_data()
        
        # Create productivity trend graph using plotly
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['Date'],
            y=df['Productivity Score'],
            mode='lines+markers',
            name='Productivity'
        ))
        
        fig.update_layout(
            title='Productivity Trend',
            xaxis_title='Date',
            yaxis_title='Productivity Score',
            height=400
        )
        
        # Save the graph as an image
        img_path = f'reports/temp_graph_{self.user.id}.png'
        fig.write_image(img_path)
        
        # Add the image to PDF
        pdf.add_page()
        pdf.image(img_path, x=10, y=10, w=190)
        
        # Clean up temporary file
        os.remove(img_path)

    def _add_activity_breakdown(self, pdf):
        df = self._prepare_data()
        
        # Create activity breakdown pie chart
        activity_data = df.groupby('Activity Type')['Duration (hours)'].sum()
        
        fig = go.Figure(data=[go.Pie(
            labels=activity_data.index,
            values=activity_data.values,
            hole=.3
        )])
        
        fig.update_layout(
            title='Activity Breakdown',
            height=400
        )
        
        # Save the graph as an image
        img_path = f'reports/temp_pie_{self.user.id}.png'
        fig.write_image(img_path)
        
        # Add the image to PDF
        pdf.add_page()
        pdf.image(img_path, x=10, y=10, w=190)
        
        # Clean up temporary file
        os.remove(img_path)

from fpdf import FPDF
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import io
import base64
from datetime import datetime, timedelta
import os

class PDFGenerator:
    def __init__(self):
        self.pdf = FPDF()
        self.pdf.add_page()
        self.pdf.set_font('Arial', 'B', 16)
        
    def add_header(self, title):
        """Adiciona cabeçalho ao PDF"""
        self.pdf.cell(0, 10, title, 0, 1, 'C')
        self.pdf.cell(0, 10, f'Gerado em: {datetime.now().strftime("%d/%m/%Y %H:%M")}', 0, 1, 'C')
        self.pdf.ln(10)
        
    def add_text(self, text, font_size=12, font_style=''):
        """Adiciona texto ao PDF"""
        self.pdf.set_font('Arial', font_style, font_size)
        self.pdf.cell(0, 10, text, 0, 1, 'L')
        
    def add_table(self, headers, data):
        """Adiciona tabela ao PDF"""
        self.pdf.set_font('Arial', 'B', 10)
        
        # Cabeçalhos
        col_width = 190 / len(headers)
        for header in headers:
            self.pdf.cell(col_width, 10, header, 1, 0, 'C')
        self.pdf.ln()
        
        # Dados
        self.pdf.set_font('Arial', '', 9)
        for row in data:
            for item in row:
                self.pdf.cell(col_width, 8, str(item), 1, 0, 'C')
            self.pdf.ln()
            
    def add_chart_from_matplotlib(self, fig, width=180, height=100):
        """Adiciona gráfico do matplotlib ao PDF"""
        # Salvar figura em buffer
        img_buffer = io.BytesIO()
        fig.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
        img_buffer.seek(0)
        
        # Salvar temporariamente
        temp_file = f"temp_chart_{datetime.now().timestamp()}.png"
        with open(temp_file, 'wb') as f:
            f.write(img_buffer.getvalue())
        
        # Adicionar ao PDF
        self.pdf.image(temp_file, x=15, w=width)
        
        # Limpar arquivo temporário
        os.remove(temp_file)
        plt.close(fig)
        
    def save(self, filename):
        """Salva o PDF"""
        self.pdf.output(filename)
        return filename

class ReportGenerator:
    def __init__(self, conn):
        self.conn = conn
        
    def generate_user_productivity_report(self, user_id, start_date, end_date):
        """Gera relatório de produtividade do usuário"""
        pdf = PDFGenerator()
        pdf.add_header('Relatório de Produtividade do Usuário')
        
        # Buscar dados do usuário
        cursor = self.conn.cursor()
        cursor.execute('SELECT username, role FROM users WHERE id = ?', (user_id,))
        user = cursor.fetchone()
        
        pdf.add_text(f'Usuário: {user[0]}', 14, 'B')
        pdf.add_text(f'Função: {user[1]}')
        pdf.add_text(f'Período: {start_date} a {end_date}')
        pdf.pdf.ln(5)
        
        # Estatísticas gerais
        cursor.execute('''
            SELECT 
                COUNT(DISTINCT r.id) as total_rotinas,
                COUNT(c.id) as total_tarefas,
                SUM(CASE WHEN c.completed = 1 THEN 1 ELSE 0 END) as tarefas_completas,
                AVG(CASE WHEN c.completed = 1 THEN 1.0 ELSE 0.0 END) * 100 as percentual_conclusao
            FROM routines r
            LEFT JOIN checklists c ON r.id = c.routine_id
            WHERE r.user_id = ? AND r.date BETWEEN ? AND ?
        ''', (user_id, start_date, end_date))
        
        stats = cursor.fetchone()
        
        pdf.add_text('Estatísticas Gerais:', 12, 'B')
        pdf.add_text(f'Total de Rotinas: {stats[0] or 0}')
        pdf.add_text(f'Total de Tarefas: {stats[1] or 0}')
        pdf.add_text(f'Tarefas Completadas: {stats[2] or 0}')
        pdf.add_text(f'Taxa de Conclusão: {stats[3]:.1f}%' if stats[3] else 'Taxa de Conclusão: 0%')
        pdf.pdf.ln(10)
        
        # Gráfico de produtividade diária
        fig = self._create_daily_productivity_chart(user_id, start_date, end_date)
        if fig:
            pdf.add_text('Produtividade Diária:', 12, 'B')
            pdf.add_chart_from_matplotlib(fig)
            pdf.pdf.ln(10)
        
        # Detalhes das rotinas
        cursor.execute('''
            SELECT r.date, r.description, 
                   COUNT(c.id) as total_tarefas,
                   SUM(CASE WHEN c.completed = 1 THEN 1 ELSE 0 END) as completas
            FROM routines r
            LEFT JOIN checklists c ON r.id = c.routine_id
            WHERE r.user_id = ? AND r.date BETWEEN ? AND ?
            GROUP BY r.id, r.date, r.description
            ORDER BY r.date DESC
        ''', (user_id, start_date, end_date))
        
        routines = cursor.fetchall()
        
        if routines:
            pdf.add_text('Detalhes das Rotinas:', 12, 'B')
            headers = ['Data', 'Descrição', 'Tarefas', 'Completas', 'Taxa']
            data = []
            for routine in routines:
                rate = (routine[3] / routine[2] * 100) if routine[2] > 0 else 0
                data.append([
                    routine[0],
                    routine[1][:30] + '...' if len(routine[1]) > 30 else routine[1],
                    routine[2],
                    routine[3],
                    f'{rate:.1f}%'
                ])
            pdf.add_table(headers, data)
        
        filename = f'relatorio_produtividade_{user_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        return pdf.save(filename)
    
    def generate_sector_report(self, sector_id, start_date, end_date):
        """Gera relatório do setor"""
        pdf = PDFGenerator()
        pdf.add_header('Relatório de Setor')
        
        # Buscar dados do setor
        cursor = self.conn.cursor()
        cursor.execute('SELECT name, description FROM sectors WHERE id = ?', (sector_id,))
        sector = cursor.fetchone()
        
        pdf.add_text(f'Setor: {sector[0]}', 14, 'B')
        pdf.add_text(f'Descrição: {sector[1] or "Não informada"}')
        pdf.add_text(f'Período: {start_date} a {end_date}')
        pdf.pdf.ln(5)
        
        # Estatísticas do setor
        cursor.execute('''
            SELECT 
                COUNT(DISTINCT u.id) as total_usuarios,
                COUNT(DISTINCT r.id) as total_rotinas,
                COUNT(c.id) as total_tarefas,
                SUM(CASE WHEN c.completed = 1 THEN 1 ELSE 0 END) as tarefas_completas
            FROM users u
            LEFT JOIN routines r ON u.id = r.user_id AND r.date BETWEEN ? AND ?
            LEFT JOIN checklists c ON r.id = c.routine_id
            WHERE u.sector_id = ?
        ''', (start_date, end_date, sector_id))
        
        stats = cursor.fetchone()
        
        pdf.add_text('Estatísticas do Setor:', 12, 'B')
        pdf.add_text(f'Total de Usuários: {stats[0] or 0}')
        pdf.add_text(f'Total de Rotinas: {stats[1] or 0}')
        pdf.add_text(f'Total de Tarefas: {stats[2] or 0}')
        pdf.add_text(f'Tarefas Completadas: {stats[3] or 0}')
        
        if stats[2] and stats[2] > 0:
            completion_rate = (stats[3] / stats[2]) * 100
            pdf.add_text(f'Taxa de Conclusão: {completion_rate:.1f}%')
        pdf.pdf.ln(10)
        
        # Gráfico de comparação de usuários
        fig = self._create_user_comparison_chart(sector_id, start_date, end_date)
        if fig:
            pdf.add_text('Comparação de Produtividade por Usuário:', 12, 'B')
            pdf.add_chart_from_matplotlib(fig)
        
        filename = f'relatorio_setor_{sector_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        return pdf.save(filename)
    
    def _create_daily_productivity_chart(self, user_id, start_date, end_date):
        """Cria gráfico de produtividade diária"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT r.date,
                   COUNT(c.id) as total,
                   SUM(CASE WHEN c.completed = 1 THEN 1 ELSE 0 END) as completas
            FROM routines r
            LEFT JOIN checklists c ON r.id = c.routine_id
            WHERE r.user_id = ? AND r.date BETWEEN ? AND ?
            GROUP BY r.date
            ORDER BY r.date
        ''', (user_id, start_date, end_date))
        
        data = cursor.fetchall()
        if not data:
            return None
        
        dates = [datetime.strptime(row[0], '%Y-%m-%d') for row in data]
        completion_rates = [(row[2]/row[1]*100) if row[1] > 0 else 0 for row in data]
        
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(dates, completion_rates, marker='o', linewidth=2, markersize=6)
        ax.set_title('Taxa de Conclusão Diária (%)')
        ax.set_xlabel('Data')
        ax.set_ylabel('Taxa de Conclusão (%)')
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0, 105)
        
        # Formatação do eixo X
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        return fig
    
    def _create_user_comparison_chart(self, sector_id, start_date, end_date):
        """Cria gráfico de comparação entre usuários do setor"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT u.username,
                   COUNT(c.id) as total_tarefas,
                   SUM(CASE WHEN c.completed = 1 THEN 1 ELSE 0 END) as completas
            FROM users u
            LEFT JOIN routines r ON u.id = r.user_id AND r.date BETWEEN ? AND ?
            LEFT JOIN checklists c ON r.id = c.routine_id
            WHERE u.sector_id = ?
            GROUP BY u.id, u.username
            HAVING COUNT(c.id) > 0
            ORDER BY completas DESC
        ''', (start_date, end_date, sector_id))
        
        data = cursor.fetchall()
        if not data:
            return None
        
        usernames = [row[0] for row in data]
        completion_rates = [(row[2]/row[1]*100) if row[1] > 0 else 0 for row in data]
        
        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.bar(usernames, completion_rates, color='skyblue', edgecolor='navy', alpha=0.7)
        
        # Adicionar valores nas barras
        for bar, rate in zip(bars, completion_rates):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 1,
                   f'{rate:.1f}%', ha='center', va='bottom')
        
        ax.set_title('Taxa de Conclusão por Usuário (%)')
        ax.set_xlabel('Usuários')
        ax.set_ylabel('Taxa de Conclusão (%)')
        ax.set_ylim(0, 105)
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        return fig 
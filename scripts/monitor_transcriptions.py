#!/usr/bin/env python3
"""
Monitor de Transcrições - Acompanha processamento e calcula estatísticas
Usage: python scripts/monitor_transcriptions.py
"""
import os
import sys
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict
import statistics

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from app.models import TranscriptionTask
from app.database import DATABASE_URL

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class TranscriptionMonitor:
    def __init__(self):
        self.engine = create_engine(DATABASE_URL)
        self.Session = sessionmaker(bind=self.engine)
        self.start_time = datetime.utcnow()
        self.initial_counts = self._get_counts()
        
    def _get_counts(self) -> Dict:
        """Get current task counts by status"""
        session = self.Session()
        try:
            counts = {
                'queued': session.query(TranscriptionTask).filter_by(status='queued').count(),
                'processing': session.query(TranscriptionTask).filter_by(status='processing').count(),
                'completed': session.query(TranscriptionTask).filter_by(status='completed').count(),
                'failed': session.query(TranscriptionTask).filter_by(status='failed').count(),
            }
            counts['total'] = sum(counts.values())
            return counts
        finally:
            session.close()
    
    def _get_recent_completed(self, since: datetime) -> List[TranscriptionTask]:
        """Get tasks completed since a specific time"""
        session = self.Session()
        try:
            tasks = session.query(TranscriptionTask).filter(
                TranscriptionTask.status == 'completed',
                TranscriptionTask.completed_at >= since
            ).all()
            return tasks
        finally:
            session.close()
    
    def _calculate_stats(self, tasks: List[TranscriptionTask]) -> Dict:
        """Calculate processing statistics"""
        if not tasks:
            return None
        
        processing_times = [t.processing_time for t in tasks if t.processing_time]
        durations = [t.duration for t in tasks if t.duration]
        
        if not processing_times:
            return None
        
        return {
            'count': len(tasks),
            'avg_processing_time': statistics.mean(processing_times),
            'median_processing_time': statistics.median(processing_times),
            'min_processing_time': min(processing_times),
            'max_processing_time': max(processing_times),
            'avg_audio_duration': statistics.mean(durations) if durations else 0,
            'total_processing_time': sum(processing_times),
            'total_audio_duration': sum(durations) if durations else 0,
        }
    
    def display_status(self):
        """Display current status"""
        counts = self._get_counts()
        elapsed = datetime.utcnow() - self.start_time
        
        # Calculate changes since start
        new_completed = counts['completed'] - self.initial_counts['completed']
        new_failed = counts['failed'] - self.initial_counts['failed']
        
        # Clear screen (works on Windows)
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print("=" * 70)
        print("🎙️  MONITOR DE TRANSCRIÇÕES - Mirror.ia")
        print("=" * 70)
        print(f"⏱️  Tempo de monitoramento: {str(elapsed).split('.')[0]}")
        print(f"🕐 Iniciado em: {self.start_time.strftime('%H:%M:%S')}")
        print()
        
        print("📊 STATUS ATUAL:")
        print(f"   ⏳ Na fila:      {counts['queued']:>4} tarefas")
        print(f"   🔄 Processando:  {counts['processing']:>4} tarefas")
        print(f"   ✅ Completadas:  {counts['completed']:>4} tarefas (+{new_completed} desde início)")
        print(f"   ❌ Falhadas:     {counts['failed']:>4} tarefas (+{new_failed} desde início)")
        print(f"   📝 TOTAL:        {counts['total']:>4} tarefas")
        print()
        
        # Calculate statistics for recent tasks
        recent_tasks = self._get_recent_completed(self.start_time)
        stats = self._calculate_stats(recent_tasks)
        
        if stats:
            print("📈 ESTATÍSTICAS DE PROCESSAMENTO:")
            print(f"   🎯 Áudios processados: {stats['count']}")
            print(f"   ⏱️  Tempo médio:       {stats['avg_processing_time']:.2f}s ({stats['avg_processing_time']/60:.2f}min)")
            print(f"   📊 Mediana:           {stats['median_processing_time']:.2f}s")
            print(f"   ⚡ Mínimo:            {stats['min_processing_time']:.2f}s")
            print(f"   🐌 Máximo:            {stats['max_processing_time']:.2f}s")
            print()
            print(f"   🎵 Duração média áudio: {stats['avg_audio_duration']:.2f}s")
            print(f"   📦 Total processado:   {stats['total_audio_duration']:.2f}s de áudio")
            print()
            
            # Calculate efficiency (real-time factor)
            if stats['total_audio_duration'] > 0:
                rtf = stats['total_processing_time'] / stats['total_audio_duration']
                print(f"   ⚙️  Real-Time Factor:   {rtf:.2f}x")
                print(f"      (1.0x = processa em tempo real)")
                print()
        
        # Estimate completion time
        if counts['queued'] > 0 and stats and stats['count'] > 0:
            avg_time = stats['avg_processing_time']
            estimated_seconds = counts['queued'] * avg_time
            eta = datetime.utcnow() + timedelta(seconds=estimated_seconds)
            
            print("⏰ ESTIMATIVA:")
            print(f"   🔮 Tempo restante:  ~{estimated_seconds/60:.1f} min")
            print(f"   🎯 Conclusão em:    {eta.strftime('%H:%M:%S')}")
            print()
        
        print("=" * 70)
        print("Pressione Ctrl+C para sair e ver relatório final")
        print("=" * 70)
    
    def run(self, interval: int = 5):
        """Run continuous monitoring"""
        try:
            while True:
                self.display_status()
                time.sleep(interval)
        except KeyboardInterrupt:
            self.show_final_report()
    
    def show_final_report(self):
        """Show final report when monitoring stops"""
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print()
        print("=" * 70)
        print("📋 RELATÓRIO FINAL - Monitor de Transcrições")
        print("=" * 70)
        
        elapsed = datetime.utcnow() - self.start_time
        print(f"⏱️  Tempo total de monitoramento: {str(elapsed).split('.')[0]}")
        print()
        
        # Get all completed tasks during monitoring
        recent_tasks = self._get_recent_completed(self.start_time)
        stats = self._calculate_stats(recent_tasks)
        
        if stats and stats['count'] > 0:
            print("📊 PROCESSAMENTO DURANTE MONITORAMENTO:")
            print(f"   ✅ Áudios completados: {stats['count']}")
            print()
            
            print("⏱️  TEMPO DE PROCESSAMENTO:")
            print(f"   📈 Média:    {stats['avg_processing_time']:.2f}s ({stats['avg_processing_time']/60:.2f} min)")
            print(f"   📊 Mediana:  {stats['median_processing_time']:.2f}s")
            print(f"   ⚡ Mínimo:   {stats['min_processing_time']:.2f}s")
            print(f"   🐌 Máximo:   {stats['max_processing_time']:.2f}s")
            print()
            
            print("🎵 ÁUDIOS PROCESSADOS:")
            print(f"   📈 Duração média:  {stats['avg_audio_duration']:.2f}s ({stats['avg_audio_duration']/60:.2f} min)")
            print(f"   📦 Total:          {stats['total_audio_duration']:.2f}s ({stats['total_audio_duration']/60:.2f} min)")
            print()
            
            # Real-time factor
            if stats['total_audio_duration'] > 0:
                rtf = stats['total_processing_time'] / stats['total_audio_duration']
                print("⚙️  EFICIÊNCIA:")
                print(f"   Real-Time Factor: {rtf:.2f}x")
                
                if rtf < 1.0:
                    print(f"   🚀 Processamento MAIS RÁPIDO que tempo real!")
                elif rtf < 2.0:
                    print(f"   ✅ Processamento eficiente (menos de 2x o tempo real)")
                else:
                    print(f"   ⚠️  Processamento lento (mais de 2x o tempo real)")
                print()
            
            # Throughput
            if elapsed.total_seconds() > 0:
                throughput = stats['count'] / (elapsed.total_seconds() / 60)
                print("📊 THROUGHPUT:")
                print(f"   {throughput:.2f} áudios/minuto")
                print(f"   {throughput * 60:.1f} áudios/hora")
                print()
        else:
            print("ℹ️  Nenhum áudio foi completado durante o monitoramento.")
            print()
        
        # Current status
        final_counts = self._get_counts()
        print("📋 STATUS FINAL:")
        print(f"   ⏳ Na fila:      {final_counts['queued']}")
        print(f"   🔄 Processando:  {final_counts['processing']}")
        print(f"   ✅ Completadas:  {final_counts['completed']}")
        print(f"   ❌ Falhadas:     {final_counts['failed']}")
        
        print()
        print("=" * 70)
        print("Monitor finalizado. Obrigado!")
        print("=" * 70)


if __name__ == "__main__":
    print("Iniciando monitor...")
    monitor = TranscriptionMonitor()
    monitor.run(interval=5)  # Atualiza a cada 5 segundos

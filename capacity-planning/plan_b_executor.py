#!/usr/bin/env python3
"""
Plan B Executor - Análisis Completo de Capacidad del Worker
Ejecuta todas las pruebas del Plan B según los requerimientos del documento
"""

import asyncio
import json
import time
import uuid
import psutil
import redis
from datetime import datetime
from typing import Dict, List, Any
import logging
import subprocess
import sys

# Importar nuestros módulos
from worker_bypass import WorkerCapacityTester
from worker_saturation_test import WorkerSaturationTester
from worker_sustained_test import WorkerSustainedTester

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PlanBExecutor:
    """Ejecutor completo del Plan B"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.capacity_tester = WorkerCapacityTester(redis_url)
        self.saturation_tester = WorkerSaturationTester(redis_url)
        self.sustained_tester = WorkerSustainedTester(redis_url)
        self.results = {}
        
    def check_prerequisites(self) -> bool:
        """Verificar que todos los prerequisitos estén cumplidos"""
        logger.info("Verificando prerequisitos...")
        
        try:
            # Verificar conexión a Redis
            redis_client = redis.from_url(self.redis_url)
            redis_client.ping()
            logger.info("✓ Redis conectado")
            
            # Verificar que el sistema tenga recursos suficientes
            memory = psutil.virtual_memory()
            if memory.available < 2 * 1024**3:  # 2GB
                logger.warning("⚠️ Memoria disponible baja: {:.1f}GB".format(memory.available / 1024**3))
            
            # Verificar CPU
            cpu_count = psutil.cpu_count()
            if cpu_count < 2:
                logger.warning("⚠️ Pocos cores de CPU disponibles: {}".format(cpu_count))
            
            logger.info("✓ Prerequisitos verificados")
            return True
            
        except Exception as e:
            logger.error(f"✗ Error verificando prerequisitos: {e}")
            return False
    
    def run_complete_plan_b_analysis(self) -> Dict[str, Any]:
        """Ejecutar análisis completo del Plan B"""
        logger.info("Iniciando análisis completo del Plan B")
        
        if not self.check_prerequisites():
            return {"error": "Prerequisitos no cumplidos"}
        
        # Configuraciones de prueba según el documento
        video_sizes = [50, 100]  # MB
        worker_configs = [1, 2, 4]  # procesos/hilos por nodo
        
        plan_b_results = {
            "analysis_type": "plan_b_complete",
            "timestamp": datetime.now().isoformat(),
            "configurations": {
                "video_sizes_mb": video_sizes,
                "worker_configs": worker_configs
            },
            "results": {}
        }
        
        # 1. Análisis de capacidad general
        logger.info("1. Ejecutando análisis de capacidad general...")
        try:
            capacity_results = self.capacity_tester.run_capacity_analysis()
            plan_b_results["results"]["capacity_analysis"] = capacity_results
            logger.info("✓ Análisis de capacidad completado")
        except Exception as e:
            logger.error(f"✗ Error en análisis de capacidad: {e}")
            plan_b_results["results"]["capacity_analysis"] = {"error": str(e)}
        
        # 2. Pruebas de saturación
        logger.info("2. Ejecutando pruebas de saturación...")
        try:
            saturation_results = self.saturation_tester.run_throughput_analysis(video_sizes, worker_configs)
            plan_b_results["results"]["saturation_analysis"] = saturation_results
            logger.info("✓ Pruebas de saturación completadas")
        except Exception as e:
            logger.error(f"✗ Error en pruebas de saturación: {e}")
            plan_b_results["results"]["saturation_analysis"] = {"error": str(e)}
        
        # 3. Pruebas de estabilidad
        logger.info("3. Ejecutando pruebas de estabilidad...")
        try:
            stability_results = self.sustained_tester.run_stability_analysis(video_sizes, worker_configs, 5)
            plan_b_results["results"]["stability_analysis"] = stability_results
            logger.info("✓ Pruebas de estabilidad completadas")
        except Exception as e:
            logger.error(f"✗ Error en pruebas de estabilidad: {e}")
            plan_b_results["results"]["stability_analysis"] = {"error": str(e)}
        
        # 4. Generar resumen consolidado
        logger.info("4. Generando resumen consolidado...")
        plan_b_results["summary"] = self._generate_plan_b_summary(plan_b_results["results"])
        
        return plan_b_results
    
    def _generate_plan_b_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generar resumen consolidado del Plan B"""
        summary = {
            "execution_status": "completed",
            "total_tests": 0,
            "successful_tests": 0,
            "failed_tests": 0,
            "key_findings": [],
            "recommendations": [],
            "capacity_table": [],
            "bottleneck_analysis": {}
        }
        
        # Analizar resultados de capacidad
        if "capacity_analysis" in results and "error" not in results["capacity_analysis"]:
            capacity_data = results["capacity_analysis"]
            summary["total_tests"] += 1
            summary["successful_tests"] += 1
            
            # Extraer tabla de capacidad
            if "results" in capacity_data:
                for result in capacity_data["results"]:
                    capacity_entry = {
                        "video_size_mb": result["video_size_mb"],
                        "workers": result["workers"],
                        "capacity_videos_per_min": result.get("capacity_videos_per_min", 0),
                        "stable": result.get("stable", False)
                    }
                    summary["capacity_table"].append(capacity_entry)
        
        # Analizar resultados de saturación
        if "saturation_analysis" in results and "error" not in results["saturation_analysis"]:
            saturation_data = results["saturation_analysis"]
            summary["total_tests"] += 1
            summary["successful_tests"] += 1
            
            # Extraer hallazgos clave
            if "summary" in saturation_data:
                summary["key_findings"].append({
                    "type": "saturation",
                    "max_throughput": saturation_data["summary"].get("max_throughput", 0),
                    "best_config": saturation_data["summary"].get("best_configuration", {})
                })
        
        # Analizar resultados de estabilidad
        if "stability_analysis" in results and "error" not in results["stability_analysis"]:
            stability_data = results["stability_analysis"]
            summary["total_tests"] += 1
            summary["successful_tests"] += 1
            
            # Extraer métricas de estabilidad
            if "summary" in stability_data:
                stability_metrics = stability_data["summary"].get("stability_metrics", {})
                summary["key_findings"].append({
                    "type": "stability",
                    "stability_rate": stability_metrics.get("stability_rate", 0),
                    "stable_configs": stability_metrics.get("stable_count", 0)
                })
        
        # Calcular estadísticas
        summary["failed_tests"] = summary["total_tests"] - summary["successful_tests"]
        
        # Generar recomendaciones
        summary["recommendations"] = self._generate_recommendations(summary)
        
        return summary
    
    def _generate_recommendations(self, summary: Dict[str, Any]) -> List[str]:
        """Generar recomendaciones basadas en los resultados"""
        recommendations = []
        
        # Analizar tabla de capacidad
        if summary["capacity_table"]:
            # Encontrar mejor configuración
            best_config = max(summary["capacity_table"], 
                            key=lambda x: x["capacity_videos_per_min"])
            
            recommendations.append(
                f"Mejor configuración: {best_config['video_size_mb']}MB, "
                f"{best_config['workers']} workers → "
                f"{best_config['capacity_videos_per_min']:.1f} videos/min"
            )
        
        # Analizar hallazgos clave
        for finding in summary["key_findings"]:
            if finding["type"] == "saturation":
                if finding["max_throughput"] > 0:
                    recommendations.append(
                        f"Throughput máximo alcanzado: {finding['max_throughput']:.1f} videos/min"
                    )
            
            elif finding["type"] == "stability":
                if finding["stability_rate"] < 0.8:
                    recommendations.append(
                        "Considerar optimizar configuración para mejorar estabilidad"
                    )
        
        # Recomendaciones generales
        if summary["failed_tests"] > 0:
            recommendations.append(
                f"Revisar {summary['failed_tests']} pruebas fallidas"
            )
        
        return recommendations
    
    def save_results(self, results: Dict[str, Any], filename: str = None) -> str:
        """Guardar resultados en archivo"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"capacity-planning/plan_b_results_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Resultados guardados en: {filename}")
        return filename
    
    def print_summary(self, results: Dict[str, Any]):
        """Imprimir resumen de resultados"""
        print(f"\n{'='*80}")
        print("ANÁLISIS DE CAPACIDAD - PLAN B (RENDIMIENTO DE LA CAPA WORKER)")
        print(f"{'='*80}")
        
        if "summary" in results:
            summary = results["summary"]
            
            print(f"Estado de ejecución: {summary['execution_status']}")
            print(f"Pruebas totales: {summary['total_tests']}")
            print(f"Pruebas exitosas: {summary['successful_tests']}")
            print(f"Pruebas fallidas: {summary['failed_tests']}")
            
            print(f"\n{'='*50}")
            print("TABLA DE CAPACIDAD")
            print(f"{'='*50}")
            
            if summary["capacity_table"]:
                print(f"{'Video Size (MB)':<15} {'Workers':<8} {'Capacity (videos/min)':<20} {'Stable':<8}")
                print("-" * 60)
                
                for entry in summary["capacity_table"]:
                    stable_str = "✓" if entry["stable"] else "✗"
                    print(f"{entry['video_size_mb']:<15} {entry['workers']:<8} "
                          f"{entry['capacity_videos_per_min']:<20.1f} {stable_str:<8}")
            else:
                print("No hay datos de capacidad disponibles")
            
            print(f"\n{'='*50}")
            print("HALLAZGOS CLAVE")
            print(f"{'='*50}")
            
            for finding in summary["key_findings"]:
                if finding["type"] == "saturation":
                    print(f"Throughput máximo: {finding['max_throughput']:.1f} videos/min")
                elif finding["type"] == "stability":
                    print(f"Tasa de estabilidad: {finding['stability_rate']:.1%}")
            
            print(f"\n{'='*50}")
            print("RECOMENDACIONES")
            print(f"{'='*50}")
            
            for i, rec in enumerate(summary["recommendations"], 1):
                print(f"{i}. {rec}")

def main():
    """Función principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Plan B Executor - Análisis de Capacidad del Worker")
    parser.add_argument("--redis-url", default="redis://localhost:6379", help="URL de Redis")
    parser.add_argument("--output-file", help="Archivo de salida para resultados")
    parser.add_argument("--quick", action="store_true", help="Ejecutar versión rápida (menos configuraciones)")
    
    args = parser.parse_args()
    
    # Crear ejecutor
    executor = PlanBExecutor(args.redis_url)
    
    # Ejecutar análisis completo
    logger.info("Iniciando análisis completo del Plan B")
    results = executor.run_complete_plan_b_analysis()
    
    # Guardar resultados
    output_file = executor.save_results(results, args.output_file)
    
    # Imprimir resumen
    executor.print_summary(results)
    
    print(f"\n{'='*80}")
    print(f"Análisis completado. Resultados guardados en: {output_file}")
    print(f"{'='*80}")

if __name__ == "__main__":
    main()

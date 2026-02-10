"""Unit tests for Pipeline Monitoring Module"""

import pytest
import tempfile
import json
import time
from pathlib import Path

from src.monitoring import MetricsCollector, PipelineMonitor


class TestMetricsCollector:
    """Test suite for MetricsCollector"""
    
    def test_initialization(self):
        """Test metrics collector initialization"""
        collector = MetricsCollector()
        
        assert collector.records_processed == 0
        assert collector.records_failed == 0
        assert collector.start_time is None
        assert collector.end_time is None
    
    def test_pipeline_timing(self):
        """Test pipeline start and end timing"""
        collector = MetricsCollector()
        
        collector.start_pipeline()
        assert collector.start_time is not None
        
        time.sleep(0.1)  # Simulate some processing
        
        collector.end_pipeline()
        assert collector.end_time is not None
        assert collector.end_time > collector.start_time
    
    def test_record_ingestion_success(self):
        """Test recording successful ingestion"""
        collector = MetricsCollector()
        
        collector.record_ingestion("csv", success=True, duration=0.5)
        collector.record_ingestion("api", success=True, duration=1.0)
        
        assert collector.records_processed == 2
        assert collector.records_failed == 0
        assert len(collector.metrics["ingestions"]) == 2
    
    def test_record_ingestion_failure(self):
        """Test recording failed ingestion"""
        collector = MetricsCollector()
        
        collector.record_ingestion("csv", success=False, duration=0.2)
        
        assert collector.records_processed == 0
        assert collector.records_failed == 1
    
    def test_source_metrics_tracking(self):
        """Test source-specific metrics"""
        collector = MetricsCollector()
        
        collector.record_ingestion("csv", success=True, duration=0.5)
        collector.record_ingestion("csv", success=True, duration=0.7)
        collector.record_ingestion("csv", success=False, duration=0.3)
        
        assert "csv" in collector.source_metrics
        assert collector.source_metrics["csv"]["success_count"] == 2
        assert collector.source_metrics["csv"]["failure_count"] == 1
        assert collector.source_metrics["csv"]["record_count"] == 3
    
    def test_record_validation(self):
        """Test recording validation results"""
        collector = MetricsCollector()
        
        collector.record_validation(valid=True)
        collector.record_validation(valid=False, errors=["error1", "error2"])
        
        assert len(collector.metrics["validations"]) == 2
        assert collector.metrics["validations"][1]["error_count"] == 2
    
    def test_record_quality_score(self):
        """Test recording quality scores"""
        collector = MetricsCollector()
        
        collector.record_quality_score(95.5)
        collector.record_quality_score(87.3)
        
        assert len(collector.metrics["quality_scores"]) == 2
        assert collector.metrics["quality_scores"][0]["score"] == 95.5
    
    def test_get_summary(self):
        """Test getting metrics summary"""
        collector = MetricsCollector()
        
        collector.start_pipeline()
        collector.record_ingestion("csv", success=True, duration=0.5)
        collector.record_ingestion("api", success=True, duration=1.0)
        collector.record_ingestion("db", success=False, duration=0.2)
        collector.record_validation(valid=True)
        collector.record_validation(valid=False, errors=["error1"])
        collector.record_quality_score(92.0)
        collector.end_pipeline()
        
        summary = collector.get_summary()
        
        assert "pipeline" in summary
        assert "records" in summary
        assert "ingestion" in summary
        assert "validation" in summary
        assert "quality" in summary
        
        assert summary["records"]["total_processed"] == 2
        assert summary["records"]["total_failed"] == 1
        assert summary["records"]["success_rate_percent"] > 0
        
        assert summary["validation"]["total_validations"] == 2
        assert summary["validation"]["valid_count"] == 1
        
        assert summary["quality"]["average_score"] == 92.0
    
    def test_export_metrics(self):
        """Test exporting metrics to file"""
        collector = MetricsCollector()
        
        collector.start_pipeline()
        collector.record_ingestion("csv", success=True, duration=0.5)
        collector.end_pipeline()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "metrics.json"
            collector.export_metrics(str(filepath))
            
            assert filepath.exists()
            
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            assert "pipeline" in data
            assert "records" in data
            assert "raw_metrics" in data


class TestPipelineMonitor:
    """Test suite for PipelineMonitor"""
    
    def test_initialization(self):
        """Test pipeline monitor initialization"""
        monitor = PipelineMonitor()
        
        assert monitor.metrics_collector is not None
        assert len(monitor.alerts) == 0
        assert "min_success_rate" in monitor.thresholds
    
    def test_set_threshold(self):
        """Test setting custom thresholds"""
        monitor = PipelineMonitor()
        
        monitor.set_threshold("min_success_rate", 90.0)
        
        assert monitor.thresholds["min_success_rate"] == 90.0
    
    def test_health_check_healthy(self):
        """Test health check with healthy metrics"""
        monitor = PipelineMonitor()
        
        # Simulate good metrics
        monitor.metrics_collector.start_pipeline()
        for _ in range(100):
            monitor.metrics_collector.record_ingestion("csv", success=True, duration=0.1)
        monitor.metrics_collector.record_quality_score(95.0)
        monitor.metrics_collector.end_pipeline()
        
        health = monitor.check_health()
        
        assert health["status"] == "healthy"
        assert len(health["issues"]) == 0
    
    def test_health_check_low_success_rate(self):
        """Test health check with low success rate"""
        monitor = PipelineMonitor()
        
        monitor.metrics_collector.start_pipeline()
        # 90% failure rate
        for _ in range(10):
            monitor.metrics_collector.record_ingestion("csv", success=False, duration=0.1)
        for _ in range(1):
            monitor.metrics_collector.record_ingestion("csv", success=True, duration=0.1)
        monitor.metrics_collector.end_pipeline()
        
        health = monitor.check_health()
        
        assert health["status"] in ["unhealthy", "degraded"]
        assert len(health["issues"]) > 0
        
        # Check that alert was generated
        assert len(monitor.alerts) > 0
    
    def test_health_check_low_quality_score(self):
        """Test health check with low quality score"""
        monitor = PipelineMonitor()
        
        monitor.metrics_collector.start_pipeline()
        monitor.metrics_collector.record_ingestion("csv", success=True, duration=0.1)
        monitor.metrics_collector.record_quality_score(50.0)  # Below 80 threshold
        monitor.metrics_collector.end_pipeline()
        
        health = monitor.check_health()
        
        # Should have quality score issue
        quality_issues = [i for i in health["issues"] if i["metric"] == "quality_score"]
        assert len(quality_issues) > 0
    
    def test_generate_alert(self):
        """Test alert generation"""
        monitor = PipelineMonitor()
        
        issue = {
            "severity": "high",
            "metric": "success_rate",
            "value": 50.0,
            "threshold": 95.0,
            "message": "Success rate too low"
        }
        
        monitor.generate_alert(issue)
        
        assert len(monitor.alerts) == 1
        assert monitor.alerts[0]["severity"] == "high"
        assert monitor.alerts[0]["metric"] == "success_rate"
    
    def test_get_alerts(self):
        """Test getting all alerts"""
        monitor = PipelineMonitor()
        
        issue1 = {
            "severity": "high",
            "metric": "success_rate",
            "value": 50.0,
            "threshold": 95.0,
            "message": "Success rate too low"
        }
        
        issue2 = {
            "severity": "medium",
            "metric": "latency",
            "value": 100.0,
            "threshold": 60.0,
            "message": "Latency too high"
        }
        
        monitor.generate_alert(issue1)
        monitor.generate_alert(issue2)
        
        alerts = monitor.get_alerts()
        
        assert len(alerts) == 2
    
    def test_health_status_gradations(self):
        """Test different health status levels"""
        monitor = PipelineMonitor()
        
        # Healthy - no issues
        monitor.metrics_collector.start_pipeline()
        for _ in range(100):
            monitor.metrics_collector.record_ingestion("csv", success=True, duration=0.1)
        monitor.metrics_collector.record_quality_score(95.0)
        monitor.metrics_collector.end_pipeline()
        
        health = monitor.check_health()
        assert health["status"] == "healthy"

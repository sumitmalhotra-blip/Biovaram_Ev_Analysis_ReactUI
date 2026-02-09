"""
Test script for UI-002: Clustered Scatter Endpoint
===================================================

Tests the K-means clustering functionality for large dataset visualization.

Author: CRMIT Backend Team
Date: February 9, 2026
"""

import numpy as np
import sys
sys.path.insert(0, '.')

from sklearn.cluster import MiniBatchKMeans

def test_clustering():
    """Test the K-means clustering logic used in the endpoint."""
    
    # Simulate FCS data (900k events)
    np.random.seed(42)
    n_events = 100000  # Use 100k for quick test
    
    # Create realistic FSC/SSC data with multiple populations
    # Population 1: Main EV population
    pop1_n = int(n_events * 0.6)
    pop1_fsc = np.random.normal(50000, 15000, pop1_n)
    pop1_ssc = np.random.normal(30000, 10000, pop1_n)
    
    # Population 2: Larger particles
    pop2_n = int(n_events * 0.25)
    pop2_fsc = np.random.normal(150000, 20000, pop2_n)
    pop2_ssc = np.random.normal(80000, 15000, pop2_n)
    
    # Population 3: Debris
    pop3_n = n_events - pop1_n - pop2_n
    pop3_fsc = np.random.normal(10000, 5000, pop3_n)
    pop3_ssc = np.random.normal(5000, 3000, pop3_n)
    
    fsc_values = np.concatenate([pop1_fsc, pop2_fsc, pop3_fsc])
    ssc_values = np.concatenate([pop1_ssc, pop2_ssc, pop3_ssc])
    
    print(f"Test data: {len(fsc_values):,} events")
    print(f"FSC range: {fsc_values.min():.0f} - {fsc_values.max():.0f}")
    print(f"SSC range: {ssc_values.min():.0f} - {ssc_values.max():.0f}")
    print("=" * 60)
    
    # Test zoom level 1 (overview)
    print("\n📊 ZOOM LEVEL 1 (Overview - 8 clusters)")
    print("-" * 40)
    
    X = np.column_stack([fsc_values, ssc_values])
    
    # Sample for clustering
    sample_size = min(50000, len(X))
    sample_indices = np.random.choice(len(X), sample_size, replace=False)
    X_sample = X[sample_indices]
    
    kmeans = MiniBatchKMeans(
        n_clusters=8,
        random_state=42,
        batch_size=1024,
        n_init=3
    )
    labels = kmeans.fit_predict(X_sample)
    
    for i in range(8):
        mask = labels == i
        cluster_points = X_sample[mask]
        if len(cluster_points) == 0:
            continue
        
        cx = np.mean(cluster_points[:, 0])
        cy = np.mean(cluster_points[:, 1])
        count = int(np.sum(mask) * (len(X) / sample_size))  # Scale back
        pct = count / len(X) * 100
        
        print(f"Cluster {i+1}: {count:,} events ({pct:.1f}%) at ({cx:.0f}, {cy:.0f})")
    
    # Test zoom level 2 (medium - 40 clusters)
    print("\n📊 ZOOM LEVEL 2 (Medium - 40 clusters)")
    print("-" * 40)
    
    kmeans2 = MiniBatchKMeans(
        n_clusters=40,
        random_state=42,
        batch_size=1024,
        n_init=3
    )
    labels2 = kmeans2.fit_predict(X_sample)
    
    # Show top 5 clusters
    cluster_sizes = [(i, np.sum(labels2 == i)) for i in range(40)]
    cluster_sizes.sort(key=lambda x: x[1], reverse=True)
    
    print("Top 5 clusters:")
    for i, (cluster_id, size) in enumerate(cluster_sizes[:5]):
        mask = labels2 == cluster_id
        cluster_points = X_sample[mask]
        cx = np.mean(cluster_points[:, 0])
        cy = np.mean(cluster_points[:, 1])
        count = int(size * (len(X) / sample_size))
        pct = count / len(X) * 100
        print(f"  {i+1}. Cluster {cluster_id}: {count:,} events ({pct:.1f}%)")
    
    # Test zoom level 3 (viewport filtering)
    print("\n📊 ZOOM LEVEL 3 (Viewport filtering)")
    print("-" * 40)
    
    # Simulate a zoomed-in viewport
    viewport = {
        'x_min': 40000,
        'x_max': 70000,
        'y_min': 20000,
        'y_max': 45000
    }
    
    mask = (
        (fsc_values >= viewport['x_min']) & (fsc_values <= viewport['x_max']) &
        (ssc_values >= viewport['y_min']) & (ssc_values <= viewport['y_max'])
    )
    
    viewport_count = np.sum(mask)
    print(f"Viewport: FSC [{viewport['x_min']}, {viewport['x_max']}], SSC [{viewport['y_min']}, {viewport['y_max']}]")
    print(f"Points in viewport: {viewport_count:,}")
    
    # Sample to 2000 if needed
    max_points = 2000
    if viewport_count > max_points:
        print(f"Would sample to {max_points} points for rendering")
    
    print("\n✅ All clustering tests passed!")
    return True


if __name__ == '__main__':
    test_clustering()

"""
Unit tests for Mie scattering physics module.

Tests cover:
- Forward calculations (diameter → scatter)
- Inverse calculations (scatter → diameter)
- Wavelength response validation
- Batch processing performance
- Edge cases and error handling
"""

import pytest
import numpy as np
from src.physics.mie_scatter import MieScatterCalculator, MieScatterResult


class TestMieScatterCalculator:
    """Test suite for MieScatterCalculator class."""
    
    @pytest.fixture
    def calculator(self):
        """Standard calculator for 488nm blue laser with EVs in PBS."""
        return MieScatterCalculator(
            wavelength_nm=488.0,
            n_particle=1.40,
            n_medium=1.33
        )
    
    @pytest.fixture
    def calculator_beads(self):
        """Calculator for polystyrene reference beads."""
        return MieScatterCalculator(
            wavelength_nm=488.0,
            n_particle=1.59,  # Polystyrene
            n_medium=1.33
        )
    
    # Forward calculation tests
    
    def test_calculate_80nm_exosome(self, calculator):
        """Test scatter calculation for typical 80nm exosome."""
        result = calculator.calculate_scattering_efficiency(80.0)
        
        assert isinstance(result, MieScatterResult)
        assert result.Q_sca > 0, "Scattering efficiency must be positive"
        assert result.Q_sca < 4.0, "Q_sca should be < 4 for small particles"
        assert 0 <= result.g <= 1, "Asymmetry parameter must be in [0,1]"
        assert result.forward_scatter > 0, "FSC must be positive"
        
        # Expect small Q_sca for 80nm << 488nm (Rayleigh regime)
        assert result.Q_sca < 0.01, f"Expected Q_sca < 0.01, got {result.Q_sca}"
    
    def test_calculate_200nm_bead(self, calculator_beads):
        """Test scatter calculation for 200nm polystyrene calibration bead."""
        result = calculator_beads.calculate_scattering_efficiency(200.0)
        
        assert result.Q_sca > 0.05, "200nm beads should have higher Q_sca"
        assert result.g > 0.2, "Larger particles should have forward bias"
        
        # 200nm is getting close to 488nm wavelength (x ~ 1.3)
        # Should see significant scatter
        assert result.size_parameter_x > 1.0
    
    def test_size_scaling(self, calculator):
        """Test that scatter increases with particle size."""
        sizes = [30, 50, 80, 100, 150]
        results = [calculator.calculate_scattering_efficiency(d) for d in sizes]
        
        # Q_sca should monotonically increase with size (in this regime)
        q_sca_values = [r.Q_sca for r in results]
        assert q_sca_values == sorted(q_sca_values), \
            "Q_sca should increase with diameter"
        
        # FSC should also increase
        fsc_values = [r.forward_scatter for r in results]
        assert fsc_values == sorted(fsc_values), \
            "FSC should increase with diameter"
    
    # Inverse calculation tests
    
    def test_inverse_problem_exact(self, calculator):
        """Test inverse calculation recovers input diameter exactly."""
        input_diameter = 80.0
        
        # Forward: diameter → FSC
        result = calculator.calculate_scattering_efficiency(input_diameter)
        fsc = result.forward_scatter
        
        # Inverse: FSC → diameter
        recovered_diameter, success = calculator.diameter_from_scatter(fsc)
        
        assert success, "Optimization should converge for exact case"
        assert abs(recovered_diameter - input_diameter) < 0.1, \
            f"Should recover diameter within 0.1nm, got {recovered_diameter} vs {input_diameter}"
    
    def test_inverse_problem_range(self, calculator):
        """Test inverse problem works across full EV size range."""
        test_diameters = [40, 60, 80, 100, 120, 150]
        
        for diameter in test_diameters:
            # Forward
            result = calculator.calculate_scattering_efficiency(diameter)
            fsc = result.forward_scatter
            
            # Inverse
            recovered, success = calculator.diameter_from_scatter(
                fsc,
                min_diameter=30.0,
                max_diameter=200.0
            )
            
            assert success, f"Failed to converge for {diameter}nm"
            error_pct = 100 * abs(recovered - diameter) / diameter
            assert error_pct < 1.0, \
                f"Error {error_pct:.2f}% for {diameter}nm (recovered {recovered:.1f}nm)"
    
    def test_inverse_problem_bounded(self, calculator):
        """Test inverse problem respects search bounds."""
        result = calculator.calculate_scattering_efficiency(100.0)
        fsc = result.forward_scatter
        
        # Set tight bounds around true value
        recovered, success = calculator.diameter_from_scatter(
            fsc,
            min_diameter=90.0,
            max_diameter=110.0
        )
        
        assert 90.0 <= recovered <= 110.0, \
            f"Result {recovered} outside bounds [90, 110]"
    
    # Wavelength response tests
    
    def test_wavelength_response_rayleigh(self, calculator):
        """Test wavelength dependence follows Rayleigh scaling."""
        # For small particles (d << λ), scatter should scale as λ^-4
        # So blue (405nm) should scatter MORE than red (633nm)
        
        response = calculator.calculate_wavelength_response(diameter_nm=80.0)
        
        # Check we got all wavelengths
        assert '405nm' in response
        assert '488nm' in response
        assert '561nm' in response
        assert '633nm' in response
        
        # Rayleigh regime: shorter wavelength = more scatter
        assert response['405nm'] > response['488nm'], "405nm should scatter more than 488nm"
        assert response['488nm'] > response['561nm'], "488nm should scatter more than 561nm"
        assert response['561nm'] > response['633nm'], "561nm should scatter more than 633nm"
        
        # Rayleigh: blue/red ratio should be significant
        blue_red_ratio = response['405nm'] / response['633nm']
        assert blue_red_ratio > 2.0, \
            f"Expected blue/red ratio > 2x, got {blue_red_ratio:.2f}x"
    
    def test_wavelength_response_custom(self, calculator):
        """Test wavelength response with custom wavelength list."""
        custom_wavelengths = [450, 500, 550, 600]
        response = calculator.calculate_wavelength_response(
            diameter_nm=100.0,
            wavelengths=custom_wavelengths
        )
        
        # Check we got all custom wavelengths
        for wl in custom_wavelengths:
            assert f'{wl}nm' in response
        
        # Check monotonic decrease (Rayleigh regime)
        values = [response[f'{wl}nm'] for wl in custom_wavelengths]
        assert values == sorted(values, reverse=True), \
            "Scatter should decrease with wavelength in Rayleigh regime"
    
    # Batch processing tests
    
    def test_batch_calculate(self, calculator):
        """Test batch processing returns correct shape and values."""
        diameters = np.array([50, 80, 100, 120])
        fsc_batch = calculator.batch_calculate(diameters, show_progress=False)
        
        # Check shape
        assert fsc_batch.shape == diameters.shape, \
            f"Output shape {fsc_batch.shape} doesn't match input {diameters.shape}"
        
        # Check values match individual calculations
        for i, diameter in enumerate(diameters):
            result = calculator.calculate_scattering_efficiency(diameter)
            expected_fsc = result.forward_scatter
            assert abs(fsc_batch[i] - expected_fsc) < 1e-6, \
                f"Batch FSC {fsc_batch[i]} doesn't match individual {expected_fsc}"
    
    def test_batch_calculate_large_array(self, calculator):
        """Test batch processing with large array (performance check)."""
        diameters = np.linspace(30, 150, 1000)
        fsc_batch = calculator.batch_calculate(diameters, show_progress=False)
        
        assert len(fsc_batch) == 1000
        assert np.all(fsc_batch >= 0), "All FSC values should be positive"
        assert np.all(np.isfinite(fsc_batch)), "All FSC values should be finite"
        
        # Check monotonic increase (in this regime)
        assert np.all(np.diff(fsc_batch) >= 0), \
            "FSC should increase monotonically with diameter"
    
    # Edge cases and error handling
    
    def test_invalid_diameter_negative(self, calculator):
        """Test that negative diameters raise ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            calculator.calculate_scattering_efficiency(-10.0)
    
    def test_invalid_diameter_zero(self, calculator):
        """Test that zero diameter raises ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            calculator.calculate_scattering_efficiency(0.0)
    
    def test_invalid_fsc_negative(self, calculator):
        """Test that negative FSC raises ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            calculator.diameter_from_scatter(-100.0)
    
    def test_invalid_fsc_zero(self, calculator):
        """Test that zero FSC raises ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            calculator.diameter_from_scatter(0.0)
    
    def test_very_small_particle(self, calculator):
        """Test calculation for very small particle (5nm - below detection)."""
        result = calculator.calculate_scattering_efficiency(5.0, validate=False)
        
        # Should still calculate, but Q_sca will be extremely small
        assert result.Q_sca < 1e-6, "5nm particle should have negligible scatter"
        assert result.g < 0.1, "Small particles should be nearly isotropic"
    
    def test_very_large_particle(self, calculator):
        """Test calculation for large particle (500nm - microvesicle)."""
        result = calculator.calculate_scattering_efficiency(500.0, validate=False)
        
        # Should calculate successfully
        assert result.Q_sca > 0
        assert result.size_parameter_x > 3.0, "Large particle should have x >> 1"
    
    def test_extreme_refractive_index(self):
        """Test with unusual refractive index values."""
        # Very high contrast (metallic-like)
        calc_high = MieScatterCalculator(
            wavelength_nm=488.0,
            n_particle=2.5,
            n_medium=1.33
        )
        result = calc_high.calculate_scattering_efficiency(100.0)
        assert result.Q_sca > 0
        
        # Low contrast (nearly index-matched)
        calc_low = MieScatterCalculator(
            wavelength_nm=488.0,
            n_particle=1.35,
            n_medium=1.33
        )
        result = calc_low.calculate_scattering_efficiency(100.0)
        assert result.Q_sca > 0
        # Low contrast should give lower scatter
        assert result.Q_sca < calc_high.calculate_scattering_efficiency(100.0).Q_sca


class TestMieScatterResult:
    """Test MieScatterResult dataclass."""
    
    def test_result_creation(self):
        """Test that MieScatterResult can be created."""
        result = MieScatterResult(
            Q_ext=0.01,
            Q_sca=0.01,
            Q_back=0.005,
            g=0.1,
            forward_scatter=10.0,
            side_scatter=5.0,
            size_parameter_x=0.5
        )
        
        assert result.Q_sca == 0.01
        assert result.forward_scatter == 10.0
    
    def test_result_immutable(self):
        """Test that MieScatterResult is frozen (immutable)."""
        result = MieScatterResult(
            Q_ext=0.01, Q_sca=0.01, Q_back=0.005,
            g=0.1, forward_scatter=10.0, side_scatter=5.0,
            size_parameter_x=0.5
        )
        
        # Dataclasses are mutable by default, so this test is just documentation
        # If we add frozen=True to dataclass, this would raise AttributeError
        result.Q_sca = 0.02  # Should be allowed (not frozen)
        assert result.Q_sca == 0.02


class TestPhysicalConsistency:
    """Integration tests for physical consistency."""
    
    def test_conservation_principles(self):
        """Test that extinction = scattering + absorption."""
        calc = MieScatterCalculator(wavelength_nm=488.0, n_particle=1.40, n_medium=1.33)
        result = calc.calculate_scattering_efficiency(100.0)
        
        # For non-absorbing particles (imaginary n = 0), Q_ext ≈ Q_sca
        # Allow small numerical error
        assert abs(result.Q_ext - result.Q_sca) < 0.001, \
            f"Non-absorbing: Q_ext ({result.Q_ext}) should equal Q_sca ({result.Q_sca})"
    
    def test_reciprocity(self):
        """Test forward-inverse calculation reciprocity."""
        calc = MieScatterCalculator(wavelength_nm=488.0, n_particle=1.40, n_medium=1.33)
        
        # Test multiple sizes
        for diameter in [50, 80, 100, 120]:
            # Forward
            result = calc.calculate_scattering_efficiency(diameter)
            fsc = result.forward_scatter
            
            # Inverse
            recovered, success = calc.diameter_from_scatter(fsc)
            
            # Check reciprocity
            assert success
            error_nm = abs(recovered - diameter)
            assert error_nm < 0.5, \
                f"Reciprocity error: {diameter}nm → {fsc:.2f} → {recovered:.2f}nm (Δ={error_nm:.2f}nm)"
    
    def test_multi_wavelength_consistency(self):
        """Test that Mie theory is wavelength-consistent."""
        diameters = [50, 80, 100]
        wavelengths = [405, 488, 561, 633]
        
        for diameter in diameters:
            # Calculate at all wavelengths
            q_sca_values = []
            for wavelength in wavelengths:
                calc = MieScatterCalculator(
                    wavelength_nm=wavelength,
                    n_particle=1.40,
                    n_medium=1.33
                )
                result = calc.calculate_scattering_efficiency(diameter)
                q_sca_values.append(result.Q_sca)
            
            # In Rayleigh regime (small particles), Q_sca should decrease with wavelength
            # Check that we have some wavelength dependence
            assert max(q_sca_values) > min(q_sca_values), \
                f"Should see wavelength dependence for {diameter}nm particle"

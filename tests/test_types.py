"""
Unit tests for type system
"""
import pytest
from models.types import DataType


class TestDataType:
    
    def test_numeric_types(self):
        """Test numeric type detection"""
        assert DataType.INTEGER.is_numeric()
        assert DataType.FLOAT.is_numeric()
        assert not DataType.STRING.is_numeric()
        assert not DataType.BOOLEAN.is_numeric()
    
    def test_comparable_types(self):
        """Test type comparison compatibility"""
        # Same types are comparable
        assert DataType.INTEGER.is_comparable(DataType.INTEGER)
        assert DataType.STRING.is_comparable(DataType.STRING)
        
        # Numeric types are comparable with each other
        assert DataType.INTEGER.is_comparable(DataType.FLOAT)
        assert DataType.FLOAT.is_comparable(DataType.INTEGER)
        
        # Different non-numeric types are not comparable
        assert not DataType.STRING.is_comparable(DataType.BOOLEAN)
        assert not DataType.BOOLEAN.is_comparable(DataType.INTEGER)
    
    def test_compatible_assignment(self):
        """Test assignment compatibility"""
        # Same types are compatible
        assert DataType.INTEGER.is_compatible_with(DataType.INTEGER)
        assert DataType.STRING.is_compatible_with(DataType.STRING)
        
        # NULL is compatible with any type (can be assigned to any variable)
        assert DataType.INTEGER.is_compatible_with(DataType.NULL)
        assert DataType.STRING.is_compatible_with(DataType.NULL)
        
        # INTEGER can be assigned to FLOAT
        assert DataType.FLOAT.is_compatible_with(DataType.INTEGER)
        
        # But not vice versa
        assert not DataType.INTEGER.is_compatible_with(DataType.FLOAT)
    
    def test_string_representation(self):
        """Test string representation of data types"""
        assert str(DataType.INTEGER) == "integer"
        assert str(DataType.STRING) == "string"
        assert str(DataType.BOOLEAN) == "boolean"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

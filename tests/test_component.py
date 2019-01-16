from lsst.ts.laser.component import LaserComponent
from unittest.mock import Mock
import pytest

class TestLaserComponent:
    @pytest.fixture(scope="class")
    def lc(self):
        lc = LaserComponent(None)
        lc.serial = Mock()
        return lc

    @pytest.mark.parametrize('module',
                             ['CPU8000','M_CPU800','llPMKu','MaxiOPG','TK6','HV40W','DelayLin','MiniOPG','LDCO48BP',
                              'M_LDCO48'])
    def test_module_setup(self,lc,module):
        assert hasattr(lc,module)

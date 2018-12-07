"""Implements CSC classes.

"""
import logging
from lsst.ts.laser.component import LaserComponent
import salobj
import SALPY_TunableLaser
import asyncio
import enum


class LaserDetailedStateEnum(enum.Enum):
    """An enumeration class for handling the TunableLaser's substates.

    Attributes
    ----------
    DISABLEDSTATE: int
    ENABLEDSTATE: int
    FAULTSTATE: int
    OFFLINESTATE: int
    STANDBYSTATE: int
    PROPAGATINGSTATE: int

    """
    DISABLEDSTATE = 1
    ENABLEDSTATE = 2
    FAULTSTATE = 3
    OFFLINESTATE = 4
    STANDBYSTATE = 5
    PROPAGATINGSTATE = 6


class LaserCSC(salobj.BaseCsc):
    """This is the class that implements the TunableLaser CSC.

    Parameters
    ----------
    address
    frequency: optional
    initial_state: optional

    Attributes
    ----------
    model
    frequency
    wavelength_topic
    temperature_topic
    summary_state

    """
    def __init__(self,address,frequency=1, initial_state=salobj.State.STANDBY):
        super().__init__(SALPY_TunableLaser)
        self.model = LaserModel(address)
        self.frequency = frequency
        self.wavelength_topic = self.tel_wavelength.DataType()
        self.temperature_topic = self.tel_temperature.DataType()
        self.summary_state = initial_state
        asyncio.ensure_future(self.telemetry())

    async def telemetry(self):
        """Sends out laser's telemetry.

        Returns
        -------

        """
        while True:
            self.model.publish()
            if self.model.fault_code == "0002H":
                self.fault()
            self.wavelength_topic.wavelength = float(self.model._laser.MaxiOPG.wavelength[:-2])
            self.temperature_topic.temperature = float(self.model._laser.TK6.temperature[:-1])
            self.tel_wavelength.put(self.wavelength_topic)
            self.tel_temperature.put(self.temperature_topic)
            await asyncio.sleep(self.frequency)

    def assert_propagating(self, action):
        """Asserts that the action is happening while in the PropagatingState.

        Parameters
        ----------
        action
            The command being sent.

        Returns
        -------

        """
        if self.detailed_state != LaserDetailedStateEnum.PROPAGATINGSTATE:
            raise salobj.ExpectedError(f"{action} not allowed in state {self.detailed_state}")

    async def do_changeWavelength(self,id_data):
        """Changes the wavelength of the laser.

        Parameters
        ----------
        id_data

        Returns
        -------

        """
        self.assert_enabled("changeWavelength")
        self.model.change_wavelength(id_data.data.wavelength)

    async def do_startPropagateLaser(self,id_data):
        """Changes the state to the Propagating State of the laser.

        Parameters
        ----------
        id_data

        Returns
        -------

        """
        self.assert_enabled("startPropagateLaser")
        self.model.run()
        self.detailed_state = LaserDetailedStateEnum.PROPAGATINGSTATE

    async def do_stopPropagateLaser(self,id_data):
        """Stops the Propagating State of the laser.

        Parameters
        ----------
        id_data

        Returns
        -------

        """
        self.assert_enabled("stopPropagateLaser")
        self.assert_propagating("stopPropagateLaser")
        self.model.stop()
        self.detailed_state = LaserDetailedStateEnum.ENABLEDSTATE

    async def do_abort(self,id_data):
        """Actually does nothing and is not implemented yet.

        Parameters
        ----------
        id_data

        Returns
        -------

        """
        pass

    async def do_clearFaultState(self, id_data):
        """Clears the fault state of the laser by turning the power register off.

        Parameters
        ----------
        id_data

        Returns
        -------

        """
        self.model.stop()


    async def do_setValue(self, id_data):
        """Actually does nothing and is not implemented yet.

        Parameters
        ----------
        id_data

        Returns
        -------

        """
        pass

    async def do_enterControl(self, id_data):
        """Does nothing because it is not implemented. It also is not necessary for the use of this laser.

        Parameters
        ----------
        id_data

        Returns
        -------

        """
        pass

    @property
    def detailed_state(self):
        detailed_state_topic = self.evt_detailedState.DataType()
        return detailed_state_topic.detailedState

    @detailed_state.setter
    def detailed_state(self,new_sub_state):
        detailed_state_topic = self.evt_detailedState.DataType()
        detailed_state_topic.detailedState = new_sub_state
        self.evt_detailedState.put(detailed_state_topic)

    def begin_enable(self, id_data):
        """A temporary hook that sets up the laser for propagation so that it is ready to go.

        Parameters
        ----------
        id_data

        Returns
        -------

        """
        self.model._laser.MaxiOPG.set_configuration("No SCU")
        self.model._laser.M_CPU800.set_energy("MAX")


class LaserModel:
    """This is the model class for the MVC paradigm.

    Parameters
    ----------
    port

    """
    def __init__(self,port):
        self._laser = LaserComponent(port)

    def change_wavelength(self,wavelength):
        """Changes the wavelength of the laser.

        Parameters
        ----------
        wavelength

        Returns
        -------

        """
        self._laser.MaxiOPG.set_wavelength(wavelength)

    def run(self):
        """Propagates the laser.

        Returns
        -------

        """
        self._laser.M_CPU800.set_propagate("ON")

    def stop(self):
        """Stops propagating the laser.

        Returns
        -------

        """
        self._laser.M_CPU800.set_propagate("OFF")

    def publish(self):
        """Updates the laser's attributes.

        Returns
        -------

        """
        self._laser._publish()


class LaserDeveloperRemote:
    """This is a class for development purposes.

    This class implements a developer remote for sending commands to the standing CSC.

    Attributes
    ----------
    remote
    log

    """
    def __init__(self):
        self.remote = salobj.Remote(SALPY_TunableLaser)
        self.log = logging.getLogger(__name__)

    async def standby(self,timeout=10):
        """Standby command

        Parameters
        ----------
        timeout

        Returns
        -------

        """
        standby_topic = self.remote.cmd_standby.DataType()
        standby_ack = await self.remote.cmd_standby.start(standby_topic,timeout=timeout)
        self.log.info(standby_ack.ack.ack)

    async def start(self,timeout=10):
        """Start command

        Parameters
        ----------
        timeout

        Returns
        -------

        """
        start_topic = self.remote.cmd_start.DataType()
        start_ack = await self.remote.cmd_start.start(start_topic,timeout=timeout)
        self.log.info(start_ack.ack.ack)

    async def enable(self,timeout=10):
        """Enable command

        Parameters
        ----------
        timeout

        Returns
        -------

        """
        enable_topic = self.remote.cmd_enable.DataType()
        enable_ack = await self.remote.cmd_enable.start(enable_topic,timeout=timeout)
        self.log.info(enable_ack.ack.ack)

    async def disable(self,timeout=10):
        """Disable command

        Parameters
        ----------
        timeout

        Returns
        -------

        """
        disable_topic = self.remote.cmd_disable.DataType()
        disable_ack = await self.remote.cmd_disable.start(disable_topic,timeout=timeout)
        self.log.info(disable_ack.ack.ack)

    async def change_wavelength(self, wavelength,timeout=10):
        """

        Parameters
        ----------
        wavelength
        timeout

        Returns
        -------

        """
        change_wavelength_topic = self.remote.cmd_changeWavelength.DataType()
        change_wavelength_topic.wavelength = float(wavelength)
        change_wavelength_ack = await self.remote.cmd_changeWavelength.start(change_wavelength_topic,timeout=timeout)
        self.log.info(change_wavelength_ack.ack.ack)

    async def start_propagate_laser(self,timeout=10):
        """startPropagate command

        Parameters
        ----------
        timeout

        Returns
        -------

        """
        start_propagate_laser_topic = self.remote.cmd_startPropagateLaser.DataType()
        start_propagate_laser_ack = await self.remote.cmd_startPropagateLaser.start(start_propagate_laser_topic,timeout=timeout)
        self.log.info(start_propagate_laser_ack.ack.ack)

    async def stop_propagate_laser(self,timeout=10):
        """stopPropagate command.

        Parameters
        ----------
        timeout

        Returns
        -------

        """
        stop_propagate_laser_topic = self.remote.cmd_stopPropagateLaser.DataType()
        stop_propagate_laser_ack = await self.remote.cmd_stopPropagateLaser.start(stop_propagate_laser_topic,timeout=timeout)
        self.log.info(stop_propagate_laser_ack.ack.ack)
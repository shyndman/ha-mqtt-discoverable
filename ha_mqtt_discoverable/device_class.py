from enum import Enum


class BinarySensorDeviceClass(str, Enum):
    """The type of binary sensor."""

    BATTERY = "battery"
    """On means low, Off means normal."""
    BATTERY_CHARGING = "battery_charging"
    """On means charging, Off means not charging."""
    CO = "co"
    """On means carbon monoxide detected, Off means no carbon monoxide (clear)."""
    COLD = "cold"
    """On means cold, Off means normal."""
    CONNECTIVITY = "connectivity"
    """On means connected, Off means disconnected."""
    DOOR = "door"
    """On means open, Off means closed."""
    GARAGE_DOOR = "garage_door"
    """On means open, Off means closed."""
    GAS = "gas"
    """On means gas detected, Off means no gas (clear)."""
    HEAT = "heat"
    """On means hot, Off means normal."""
    LIGHT = "light"
    """On means light detected, Off means no light."""
    LOCK = "lock"
    """On means open (unlocked), Off means closed (locked)."""
    MOISTURE = "moisture"
    """On means wet, Off means dry."""
    MOTION = "motion"
    """On means motion detected, Off means no motion (clear)."""
    MOVING = "moving"
    """On means moving, Off means not moving (stopped)."""
    OCCUPANCY = "occupancy"
    """On means occupied, Off means not occupied (clear)."""
    OPENING = "opening"
    """On means open, Off means closed."""
    PLUG = "plug"
    """On means plugged in, Off means unplugged."""
    POWER = "power"
    """On means power detected, Off means no power."""
    PRESENCE = "presence"
    """On means home, Off means away."""
    PROBLEM = "problem"
    """On means problem detected, Off means no problem (OK)."""
    RUNNING = "running"
    """On means running, Off means not running."""
    SAFETY = "safety"
    """On means unsafe, Off means safe."""
    SMOKE = "smoke"
    """On means smoke detected, Off means no smoke (clear)."""
    SOUND = "sound"
    """On means sound detected, Off means no sound (clear)."""
    TAMPER = "tamper"
    """On means tampering detected, Off means no tampering (clear)"""
    UPDATE = "update"
    """On means update available, Off means up-to-date. The use of this device
    class should be avoided, please consider using the update entity instead."""
    VIBRATION = "vibration"
    """On means vibration detected, Off means no vibration."""
    WINDOW = "window"
    """On means open, Off means closed."""


class ButtonDeviceClass(str, Enum):
    """Optionally specifies the type of button. It will possibly map to Google
    device types."""

    IDENTIFY = "identify"
    """The button entity identifies a device."""
    RESTART = "restart"
    """The button entity restarts the device."""
    UPDATE = "update"
    """The button entity updates the software of the device. The use of this
    device class should be avoided, please consider using the update entity
    instead."""


class CoverDeviceClass(str, Enum):
    AWNING = "awning"
    """Control of an awning, such as an exterior retractible window, door, or
    patio cover."""
    BLIND = "blind"
    """Control of blinds, which are linked slats that expand or collapse to
    cover an opening or may be tilted to partially cover an opening, such as
    window blinds."""
    CURTAIN = "curtain"
    """Control of curtains or drapes, which is often fabric hung above a window
    or door that can be drawn open."""
    DAMPER = "damper"
    """Control of a mechanical damper that reduces air flow, sound, or light."""
    DOOR = "door"
    """Control of a door that provides access to an area which is typically part
    of a structure."""
    GARAGE = "garage"
    """Control of a garage door that provides access to a garage."""
    GATE = "gate"
    """Control of a gate that provides access to a driveway or other area. Gates
    are found outside of a structure and are typically part of a fence."""
    SHADE = "shade"
    """Control of shades, which are a continuous plane of material or connected
    cells that expanded or collapsed over an opening, such as window shades."""
    SHUTTER = "shutter"
    """Control of shutters, which are linked slats that swing out/in to cover an
    opening or may be tilted to partially cover an opening, such as indoor or
    exterior window shutters."""
    WINDOW = "window"
    """Control of a physical window that opens and closes or may tilt."""


class EventDeviceClass(str, Enum):
    BUTTON = "button"
    """A button of a remote control has been pressed."""
    DOORBELL = "doorbell"
    """Specifically for buttons that are used as a doorbell."""
    MOTION = "motion"
    """For motion events detected by a motion sensor."""


class HumidifierDeviceClass(str, Enum):
    DEHUMIDIFIER = "dehumidifier"
    """A dehumidifier"""
    HUMIDIFIER = "humidifier"
    """A humidifier"""


class NumberDeviceClass(str, Enum):
    APPARENT_POWER = "apparent_power"
    """VA	Apparent power"""
    AQI = "aqi"
    """None	Air Quality Index"""
    AREA = "area"
    """m², cm², km², mm², in², ft², yd², mi², ac, ha	Area"""
    ATMOSPHERIC_PRESSURE = "atmospheric_pressure"
    """cbar, bar, hPa, mmHG, inHg, kPa, mbar, Pa, psi	Atmospheric pressure"""
    BATTERY = "battery"
    """%	Percentage of battery that is left"""
    BLOOD_GLUCOSE_CONCENTRATION = "blood_glucose_concentration"
    """mg/dL, mmol/L	Blood glucose concentration```"""
    CO2 = "co2"
    """ppm	Concentration of carbon dioxide."""
    CO = "co"
    """ppm	Concentration of carbon monoxide."""
    CONDUCTIVITY = "conductivity"
    """S/cm, mS/cm, µS/cm	Conductivity"""
    CURRENT = "current"
    """A, mA	Current"""
    DATA_RATE = "data_rate"
    """bit/s, kbit/s, Mbit/s, Gbit/s, B/s, kB/s, MB/s, GB/s, KiB/s, MiB/s, GiB/s	Data rate"""
    DATA_SIZE = "data_size"
    """bit, kbit, Mbit, Gbit, B, kB, MB, GB, TB, PB, EB, ZB, YB, KiB, MiB, GiB, TiB, PiB, EiB, ZiB, YiB	Data size"""
    DISTANCE = "distance"
    """km, m, cm, mm, mi, nmi, yd, in	Generic distance"""
    DURATION = "duration"
    """d, h, min, s, ms	Time period. Should not update only due to time passing. The device or service needs to give a new data point to update."""
    ENERGY = "energy"
    """J, kJ, MJ, GJ, mWh, Wh, kWh, MWh, GWh, TWh, cal, kcal, Mcal, Gcal	Energy, this device class should be used to represent energy consumption, for example an electricity meter. Represents power over time. Not to be confused with power."""
    ENERGY_DISTANCE = "energy_distance"
    """kWh/100km, mi/kWh, km/kWh	Energy per distance, this device class should be used to represent energy consumption by distance, for example the amount of electric energy consumed by an electric car."""
    ENERGY_STORAGE = "energy_storage"
    """J, kJ, MJ, GJ, mWh, Wh, kWh, MWh, GWh, TWh, cal, kcal, Mcal, Gcal	Stored energy, this device class should be used to represent stored energy, for example the amount of electric energy currently stored in a battery or the capacity of a battery. Represents power over time. Not to be confused with power."""
    FREQUENCY = "frequency"
    """Hz, kHz, MHz, GHz	Frequency"""
    GAS = "gas"
    """m³, ft³, CCF	Volume of gas. Gas consumption measured as energy in kWh instead of a volume should be classified as energy."""
    HUMIDITY = "humidity"
    """%	Relative humidity"""
    ILLUMINANCE = "illuminance"
    """lx	Light level"""
    IRRADIANCE = "irradiance"
    """W/m², BTU/(h⋅ft²)	Irradiance"""
    MOISTURE = "moisture"
    """%	Moisture"""
    MONETARY = "monetary"
    """ISO 4217	Monetary value with a currency."""
    NITROGEN_DIOXIDE = "nitrogen_dioxide"
    """µg/m³	Concentration of nitrogen dioxide"""
    NITROGEN_MONOXIDE = "nitrogen_monoxide"
    """µg/m³	Concentration of nitrogen monoxide"""
    NITROUS_OXIDE = "nitrous_oxide"
    """µg/m³	Concentration of nitrous oxide"""
    OZONE = "ozone"
    """µg/m³	Concentration of ozone"""
    PH = "ph"
    """None	Potential hydrogen (pH) of an aqueous solution"""
    PM1 = "pm1"
    """µg/m³	Concentration of particulate matter less than 1 micrometer"""
    PM25 = "pm25"
    """µg/m³	Concentration of particulate matter less than 2.5 micrometers"""
    PM10 = "pm10"
    """µg/m³	Concentration of particulate matter less than 10 micrometers"""
    POWER = "power"
    """mW, W, kW, MW, GW, TW	Power."""
    POWER_FACTOR = "power_factor"
    """%, None	Power Factor"""
    PRECIPITATION = "precipitation"
    """cm, in, mm	Accumulated precipitation"""
    PRECIPITATION_INTENSITY = "precipitation_intensity"
    """in/d, in/h, mm/d, mm/h	Precipitation intensity"""
    PRESSURE = "pressure"
    """cbar, bar, hPa, mmHg, inHg, kPa, mbar, Pa, psi	Pressure."""
    REACTIVE_POWER = "reactive_power"
    """var	Reactive power"""
    SIGNAL_STRENGTH = "signal_strength"
    """dB, dBm	Signal strength"""
    SOUND_PRESSURE = "sound_pressure"
    """dB, dBA	Sound pressure"""
    SPEED = "speed"
    """ft/s, in/d, in/h, in/s, km/h, kn, m/s, mph, mm/d, mm/s	Generic speed"""
    SULPHUR_DIOXIDE = "sulphur_dioxide"
    """µg/m³	Concentration of sulphure dioxide"""
    TEMPERATURE = "temperature"
    """°C, °F, K	Temperature."""
    VOLATILE_ORGANIC_COMPOUNDS = "volatile_organic_compounds"
    """µg/m³	Concentration of volatile organic compounds"""
    VOLATILE_ORGANIC_COMPOUNDS_PARTS = "volatile_organic_compounds_parts"
    """ppm, ppb	Ratio of volatile organic compounds"""
    VOLTAGE = "voltage"
    """V, mV, µV, kV, MV	Voltage"""
    VOLUME = "volume"
    """L, mL, gal, fl. oz., m³, ft³, CCF	Generic volume, this device class should be used to represent a consumption, for example the amount of fuel consumed by a vehicle."""
    VOLUME_FLOW_RATE = "volume_flow_rate"
    """m³/h, ft³/min, L/min, gal/min, mL/s	Volume flow rate, this device class should be used to represent a flow of some volume, for example the amount of water consumed momentarily."""
    VOLUME_STORAGE = "volume_storage"
    """L, mL, gal, fl. oz., m³, ft³, CCF	Generic stored volume, this device class should be used to represent a stored volume, for example the amount of fuel in a fuel tank."""
    WATER = "water"
    """L, gal, m³, ft³, CCF	Water consumption"""
    WEIGHT = "weight"
    """kg, g, mg, µg, oz, lb, st	Generic mass; weight is used instead of mass to fit with every day language."""
    WIND_DIRECTION = "wind_direction"
    """°	Wind direction"""
    WIND_SPEED = "wind_speed"
    """ft/s, km/h, kn, m/s, mph	Wind speed"""


class SensorDeviceClass(str, Enum):
    """Type of sensor."""

    APPARENT_POWER = "apparent_power"
    """VA	Apparent power"""
    AQI = "aqi"
    """None	Air Quality Index"""
    AREA = "area"
    """m², cm², km², mm², in², ft², yd², mi², ac, ha	Area"""
    ATMOSPHERIC_PRESSURE = "atmospheric_pressure"
    """cbar, bar, hPa, mmHG, inHg, kPa, mbar, Pa, psi	Atmospheric pressure"""
    BATTERY = "battery"
    """%	Percentage of battery that is left"""
    BLOOD_GLUCOSE_CONCENTRATION = "blood_glucose_concentration"
    """mg/dL, mmol/L	Blood glucose concentration```"""
    CO2 = "co2"
    """ppm	Concentration of carbon dioxide."""
    CO = "co"
    """ppm	Concentration of carbon monoxide."""
    CONDUCTIVITY = "conductivity"
    """S/cm, mS/cm, µS/cm	Conductivity"""
    CURRENT = "current"
    """A, mA	Current"""
    DATA_RATE = "data_rate"
    """bit/s, kbit/s, Mbit/s, Gbit/s, B/s, kB/s, MB/s, GB/s, KiB/s, MiB/s, GiB/s	Data rate"""
    DATA_SIZE = "data_size"
    """bit, kbit, Mbit, Gbit, B, kB, MB, GB, TB, PB, EB, ZB, YB, KiB, MiB, GiB, TiB, PiB, EiB, ZiB, YiB	Data size"""
    DATE = "date"
    """	Date. Requires native_value to be a Python datetime.date object, or None."""
    DISTANCE = "distance"
    """km, m, cm, mm, mi, nmi, yd, in	Generic distance"""
    DURATION = "duration"
    """d, h, min, s, ms	Time period. Should not update only due to time passing. The device or service needs to give a new data point to update."""
    ENERGY = "energy"
    """J, kJ, MJ, GJ, mWh, Wh, kWh, MWh, GWh, TWh, cal, kcal, Mcal, Gcal	Energy, this device class should be used for sensors representing energy consumption, for example an electricity meter. Represents power over time. Not to be confused with power."""
    ENERGY_DISTANCE = "energy_distance"
    """kWh/100km, mi/kWh, km/kWh	Energy per distance, this device class should be used to represent energy consumption by distance, for example the amount of electric energy consumed by an electric car."""
    ENERGY_STORAGE = "energy_storage"
    """J, kJ, MJ, GJ, mWh, Wh, kWh, MWh, GWh, TWh, cal, kcal, Mcal, Gcal	Stored energy, this device class should be used for sensors representing stored energy, for example the amount of electric energy currently stored in a battery or the capacity of a battery. Represents power over time. Not to be confused with power."""
    ENUM = "enum"
    """	The sensor has a limited set of (non-numeric) states. The options property must be set to a list of possible states when using this device class."""
    FREQUENCY = "frequency"
    """Hz, kHz, MHz, GHz	Frequency"""
    GAS = "gas"
    """m³, ft³, CCF	Volume of gas. Gas consumption measured as energy in kWh instead of a volume should be classified as energy."""
    HUMIDITY = "humidity"
    """%	Relative humidity"""
    ILLUMINANCE = "illuminance"
    """lx	Light level"""
    IRRADIANCE = "irradiance"
    """W/m², BTU/(h⋅ft²)	Irradiance"""
    MOISTURE = "moisture"
    """%	Moisture"""
    MONETARY = "monetary"
    """ISO 4217	Monetary value with a currency."""
    NITROGEN_DIOXIDE = "nitrogen_dioxide"
    """µg/m³	Concentration of nitrogen dioxide"""
    NITROGEN_MONOXIDE = "nitrogen_monoxide"
    """µg/m³	Concentration of nitrogen monoxide"""
    NITROUS_OXIDE = "nitrous_oxide"
    """µg/m³	Concentration of nitrous oxide"""
    OZONE = "ozone"
    """µg/m³	Concentration of ozone"""
    PH = "ph"
    """None	Potential hydrogen (pH) of an aqueous solution"""
    PM1 = "pm1"
    """µg/m³	Concentration of particulate matter less than 1 micrometer"""
    PM25 = "pm25"
    """µg/m³	Concentration of particulate matter less than 2.5 micrometers"""
    PM10 = "pm10"
    """µg/m³	Concentration of particulate matter less than 10 micrometers"""
    POWER = "power"
    """mW, W, kW, MW, GW, TW	Power."""
    POWER_FACTOR = "power_factor"
    """%, None	Power Factor"""
    PRECIPITATION = "precipitation"
    """cm, in, mm	Accumulated precipitation"""
    PRECIPITATION_INTENSITY = "precipitation_intensity"
    """in/d, in/h, mm/d, mm/h	Precipitation intensity"""
    PRESSURE = "pressure"
    """cbar, bar, hPa, mmHg, inHg, kPa, mbar, Pa, psi	Pressure."""
    REACTIVE_POWER = "reactive_power"
    """var	Reactive power"""
    SIGNAL_STRENGTH = "signal_strength"
    """dB, dBm	Signal strength"""
    SOUND_PRESSURE = "sound_pressure"
    """dB, dBA	Sound pressure"""
    SPEED = "speed"
    """ft/s, in/d, in/h, in/s, km/h, kn, m/s, mph, mm/d, mm/s	Generic speed"""
    SULPHUR_DIOXIDE = "sulphur_dioxide"
    """µg/m³	Concentration of sulphure dioxide"""
    TEMPERATURE = "temperature"
    """°C, °F, K	Temperature."""
    TIMESTAMP = "timestamp"
    """	Timestamp. Requires native_value to return a Python datetime.datetime object, with time zone information, or None."""
    VOLATILE_ORGANIC_COMPOUNDS = "volatile_organic_compounds"
    """µg/m³	Concentration of volatile organic compounds"""
    VOLATILE_ORGANIC_COMPOUNDS_PARTS = "volatile_organic_compounds_parts"
    """ppm, ppb	Ratio of volatile organic compounds"""
    VOLTAGE = "voltage"
    """V, mV, µV, kV, MV	Voltage"""
    VOLUME = "volume"
    """L, mL, gal, fl. oz., m³, ft³, CCF	Generic volume, this device class should be used for sensors representing a consumption, for example the amount of fuel consumed by a vehicle."""
    VOLUME_FLOW_RATE = "volume_flow_rate"
    """m³/h, ft³/min, L/min, gal/min, mL/s	Volume flow rate, this device class should be used for sensors representing a flow of some volume, for example the amount of water consumed momentarily."""
    VOLUME_STORAGE = "volume_storage"
    """L, mL, gal, fl. oz., m³, ft³, CCF	Generic stored volume, this device class should be used for sensors representing a stored volume, for example the amount of fuel in a fuel tank."""
    WATER = "water"
    """L, gal, m³, ft³, CCF	Water consumption"""
    WEIGHT = "weight"
    """kg, g, mg, µg, oz, lb, st	Generic mass; weight is used instead of mass to fit with every day language."""
    WIND_DIRECTION = "wind_direction"
    """°	Wind direction"""
    WIND_SPEED = "wind_speed"
    """ft/s, km/h, kn, m/s, mph	Wind speed"""


class SwitchDeviceClass(str, Enum):
    OUTLET = "outlet"
    """Device is an outlet for power."""
    SWITCH = "switch"
    """Device is switch for some type of entity."""


class ValveDeviceClass(str, Enum):
    """Optionally specifies the type of valve."""

    WATER = "water"
    """Control of a water valve."""
    GAS = "gas"
    """Control of a gas valve."""


class UpdateDeviceClass(str, Enum):
    """Optionally specifies the type of update."""

    FIRMWARE = "firmware"
    """The update is a firmware update for a device."""

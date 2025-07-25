# Changelog

All notable changes to the TFT32 Moonraker Plugin will be documented in this file.

## [1.1.0] - 2025-01-25

### 🚀 Enhanced Features Release ✅

#### Added
- **Layer Information Display**: TFT now shows current layer / total layers
- **Auto-Update Integration**: Moonraker update manager support
- **Enhanced Print Progress**: Data Left, Time Left, Layer Left notifications
- **Virtual SD Card Integration**: Better file progress tracking
- **Auto-Update Configuration**: Easy setup for automatic updates via Git

#### Technical Improvements
- **Extended Klipper Queries**: Added virtual_sdcard object querying
- **Layer Progress Estimation**: Basic layer tracking implementation
- **Moonraker Update Manager**: Git repository integration
- **Enhanced Progress Updates**: Multiple progress notification types

#### Configuration
- **Auto-Update Config**: `moonraker_update_config.conf` template
- **Update Manager Integration**: Automatic updates via Mainsail/Fluidd
- **Version Rollback Support**: Safe update management

#### Build Status
- **Unit Tests**: ✅ PASSED
- **Integration Tests**: ✅ PASSED  
- **Hardware Tests**: ✅ PASSED
- **Documentation**: ✅ UPDATED
- **Auto-Update**: ✅ VERIFIED

## [1.0.0] - 2025-01-25

### 🚀 Initial Release - STABLE BUILD ✅

#### Added
- **Moonraker Plugin Architecture**: Native integration with Moonraker component system
- **Display-Only Mode**: Reliable one-way communication for printer monitoring
- **Auto Firmware Detection**: Supports MKS and BIGTREETECH TFT firmware
- **Real-Time Data Streaming**: Live temperatures, print progress, fan speed, position
- **Print Status Integration**: Full M118 action codes (start/pause/resume/end/cancel)
- **Automated Installation**: One-command installer with dependency management
- **Configuration Management**: Template-based setup with common configurations
- **Version Tracking**: Semantic versioning with build status indicators

#### Technical Features
- **Klipper Integration**: Direct access via klippy_apis component
- **Serial Communication**: UART/GPIO connection with configurable baud rates
- **Error Handling**: Graceful fallbacks and connection recovery
- **Logging Optimization**: Minimal logging for reduced log file size
- **Component Safety**: Safe initialization order and component availability checks

#### Tested Hardware
- ✅ BIGTREETECH TFT32 (115200 baud)
- ✅ Raspberry Pi 3/4 (GPIO UART)
- ✅ Moonraker + Klipper setup

#### Documentation
- Complete README with installation guide
- Hardware connection diagrams
- Troubleshooting section
- Configuration examples
- API documentation

#### Build Status
- **Unit Tests**: ✅ PASSED
- **Integration Tests**: ✅ PASSED  
- **Hardware Tests**: ✅ PASSED
- **Documentation**: ✅ COMPLETE
- **Code Quality**: ✅ VERIFIED

---

## Development History

This project evolved through extensive testing and refinement:

1. **Initial Research**: TFT32 hardware analysis and firmware investigation
2. **Protocol Development**: G-code emulation and M118 action code implementation
3. **Moonraker Integration**: Component architecture and API integration
4. **Hardware Testing**: Real-world validation with multiple TFT configurations
5. **Production Hardening**: Error handling, logging optimization, and stability improvements

## Future Roadmap

- **v1.1.0**: Enhanced TFT firmware support (MKS Original, additional models)
- **v1.2.0**: Configuration web interface integration
- **v2.0.0**: Two-way communication support (if hardware allows) 
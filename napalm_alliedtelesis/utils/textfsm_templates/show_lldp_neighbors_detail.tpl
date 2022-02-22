Value LOCAL_PORT (\S+)
Value CHASSIS_ID (.*)
Value REMOTE_SYSTEM_NAME (.*)
Value REMOTE_PORT (.*)
Value REMOTE_PORT_DESCRIPTION (.*)
Value List REMOTE_SYSTEM_DESCRIPTION (.*)
Value List REMOTE_SYSTEM_CAPAB (.*)
Value List REMOTE_SYSTEM_ENABLE_CABAP (.*)


Start
  ^Local ${LOCAL_PORT}: 
  ^\s+Chassis ID\s\S+\s${CHASSIS_ID}
  ^\s+Port ID\s\S+\s${REMOTE_PORT}
  ^\s+Port Description\s\S+\s${REMOTE_PORT_DESCRIPTION}
  ^\s+System Name\s\S+\s${REMOTE_SYSTEM_NAME} -> Description
#  ^  System Description ............... ${REMOTE_SYSTEM_DESCRIPTION}  
#  ^                                     ${REMOTE_SYSTEM_DESCRIPTION} 
#  ^  System Capabilities - Supported .. ${REMOTE_SYSTEM_CAPAB} 
#  ^                      - Enabled .... ${REMOTE_SYSTEM_ENABLE_CABAP} 

Description
  ^\s+System Description\s\S+\s${REMOTE_SYSTEM_DESCRIPTION} -> System
#  ^\s+System Capabilities\s-\s(Supported|\S+)\s\S+\s${REMOTE_SYSTEM_CAPAB} 
#  ^\s{2}System Capabilities\s(-\sSupported\s\S+|\S+)\s${REMOTE_SYSTEM_CAPAB} 
#  ^\s+-\sEnabled\s\S+\s${REMOTE_SYSTEM_ENABLE_CABAP} -> Record
  ^$$ -> Start

System
  ^                                     ${REMOTE_SYSTEM_DESCRIPTION} 
  ^\s{2}System Capabilities\s(-\sSupported\s\S+|\S+)\s${REMOTE_SYSTEM_CAPAB} -> Capa

Capa
  ^\W+Enabled\W+${REMOTE_SYSTEM_ENABLE_CABAP} -> Record
  ^\W+Management Addresses -> Record Start
  ^$$ -> Start



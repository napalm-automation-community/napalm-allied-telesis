Value INTERFACE (\S+)
Value IS_UP (\S+)
Value IS_ENABLED (\S+)
Value MAC_ADDRESS (\S+)
Value SPEED (\d+|\S+)
Value DESCRIPTION (\S+)
Value MTU (\d+)
Value LAST_FLAPPED (.*)







Start
  ^Interface ${INTERFACE} 
  ^\s+Link is ${IS_UP},.*is ${IS_ENABLED} 
  ^.*address is ${MAC_ADDRESS} 
  ^\s+Description: ${DESCRIPTION}
  ^\s+index\s\d+\s+metric\s\d+\smtu\s${MTU}
  ^.*current speed ${SPEED} 
  ^\s+Time since last state change:\s${LAST_FLAPPED} -> Record

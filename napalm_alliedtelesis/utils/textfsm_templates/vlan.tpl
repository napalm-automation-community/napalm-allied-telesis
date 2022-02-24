Value VLAN (\S+)
Value NAME (\S+)
Value List INTERFACES (\S+)

#Start
#  ^======= ================ ======= ======= ==================================== -> VLAN

Start
  ^\d+.* -> Continue.Record
  ^${VLAN}\s+${NAME}\s+\S+\s+\S+\s+${INTERFACES} -> Continue
  ^${VLAN}\s+${NAME}\s+\S+\s+\S+\s+\S+ +${INTERFACES} -> Continue
  ^${VLAN}\s+${NAME}\s+\S+\s+\S+\s+(\S+ +){2}${INTERFACES} -> Continue
  ^${VLAN}\s+${NAME}\s+\S+\s+\S+\s+(\S+ +){3}${INTERFACES} -> Continue
  ^\s+${INTERFACES} -> Continue
  ^\s+\S+ ${INTERFACES} -> Continue
  ^\s+(\S+ +){2}${INTERFACES} -> Continue
  ^\s+(\S+ +){3}${INTERFACES} -> Continue



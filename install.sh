#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
SERVICE_NAME=$(basename "$SCRIPT_DIR")

# set permissions for script files
chmod 755 $SCRIPT_DIR/$SERVICE_NAME.py
chmod 755 $SCRIPT_DIR/install.sh
chmod 755 $SCRIPT_DIR/restart.sh
chmod 755 $SCRIPT_DIR/uninstall.sh
chmod 755 $SCRIPT_DIR/service/run
chmod 755 $SCRIPT_DIR/service/log/run

# check dependencies
python -c "import sunspec.core.client" > /dev/null 2>&1
RET=$?

if [ $RET -gt 0 ]
then
    python -m pip install pysunspec
    RET=$?
    if [ $RET -gt 0 ]
    then
        # if pip command fails install pip and then try again
        opkg update && opkg install python3-pip
        python -m pip install pysunspec
    fi
fi

# create sym-link to run script in deamon
ln -s $SCRIPT_DIR/service /service/$SERVICE_NAME

# add install-script to rc.local to be ready for firmware update
filename=/data/rc.local
if [ ! -f $filename ]
then
    touch $filename
    chmod 755 $filename
    echo "#!/bin/bash" >> $filename
    echo >> $filename
fi

# if not already added, then add to rc.local
grep -qxF "bash $SCRIPT_DIR/install.sh" $filename || echo "bash $SCRIPT_DIR/install.sh" >> $filename

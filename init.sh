#!/bin/bash
sudo cp cert/server.pem /usr/share/ca-certificates/painfire-vm-model.pem
sudo update-ca-certificates

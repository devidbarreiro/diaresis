#!/bin/bash
find $(pwd)/uploads -type f -mtime +7 -delete
find $(pwd)/output -type f -mtime +7 -delete

#!/bin/bash
sqlite3 records.db < stars.sql
sqlite3 records.db < ss_records.sql
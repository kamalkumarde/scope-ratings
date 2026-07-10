# scope-ratings
Entry Point

1. Start Run
   1.1 Initialize the project Load 2 db connections for Data and Audit
   1.2 Load Env
       Directories/folders etc 
   1.3 Check DB objects
        

Orchestration 

2. Load file List

3. Process Each single File

   3.01 Insert Submission record.

   
   3.1 Extract Excel Fields to Json

   3.2 Validate Json
	       3.2.1 Schema Validation
	       3.2.2 Type Validation
	       3.2.3 Business Validation.
	       3.2.4 Record Inddividual Errors

   3.3 Load Valid Json  to DB 

   3.4 Load Warehouse

       3.4.1 Load DIM Entity
       3.4.2 Load DIM Profile
       3.4.3 Load DIM Ind Profile
       3.4.4 Load FCT Metric

   3.5 Log Metrics

4 Cleanup and Close Connections

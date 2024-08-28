## Overview
Global Sensitivity Analysis (GSA) is a family of methods that aim to determine which input variables are contributing the most to variations in the outcome of a stochastic model. In the context of Life Cycle Assessment (LCA), this means that GSA aims at identifying those variables (e.g. economic flows, environmental flows, characterization factors, or parameters) that due to their uncertainty distributions affect LCA results most. This provides the LCA practitioner with a shortlist of important variables for his model. For some of these variables, it may be possible to collect additional data to reduce uncertainties, which may then reduce the overall uncertainties of the LCA results. 
 
The **AB implements the delta-moment independent method** to calculate the global sensitivities. The approach is described in detail in our [scientific paper](https://onlinelibrary.wiley.com/doi/10.1111/jiec.13194). Our implementation uses the Sensitivity Analysis Library [SALib](https://github.com/SALib/SALib).

Here we describe the basic steps for performing GSA with the Activity Browser. 


## Step 1: creating a calculation setup and calculating LCA results
[How to create a calculation setup](https://github.com/LCA-ActivityBrowser/activity-browser/wiki#creating-a-calculation-setup)

## Step 2: performing Monte Carlo Simulation
Monte Carlo simulation needs to be performed in order to obtain sampled data for the LCA inputs (economic and environmental flows, characterization factors, and parameters) and the corresponding LCA results, which, together, form the required input data for the GSA. A description of how to perform Monte Carlo Simulation in the AB is provided [here](https://github.com/LCA-ActivityBrowser/activity-browser/wiki/Monte-Carlo-Simulation).
 
## Step 3: Global Sensitivity Analysis
Now the user can go to the `Sensitivity Analysis` tab to perform GSA. The figure below shows the options the user has at this level. 
* While the Monte Carlo Simulation was performed for all reference flows and impact categories at once, the GSA is performed for one reference flow and impact category at a time. This means that the user needs to **select the reference flow and impact categories** that he is interested in. GSA can be repeated later for other reference flows or impact categories based on the same Monte Carlo Simulation results. 
* The user can specify the **cut-off values **used for flows in the A (technosphere) and B (biosphere) matrices. 
* Finally, the user can **select to export both input and output data** to the GSA. If the user does not select this option, he will later only have the option to export the output data.

![GSA setup](https://user-images.githubusercontent.com/33026150/115353675-164b7e00-a1b9-11eb-8063-dfca57e5d0b3.jpg)

After the GSA is performed, the user will see a table with all input variables (environmental, economic flows, characterization factors and parameters) sorted by their delta value, which is the result of the GSA and characterizes their overall relevance. Additional data and metadata is also provided in the table.

![GSA results only delta](https://user-images.githubusercontent.com/33026150/115353671-151a5100-a1b9-11eb-8218-544a5b00ebef.jpg)
 

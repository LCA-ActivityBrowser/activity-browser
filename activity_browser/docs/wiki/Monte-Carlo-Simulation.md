[Monte Carlo Simulation](https://en.wikipedia.org/wiki/Monte_Carlo_method) is method that relies on repeated random sampling of data to produce numerical results for uncertain input data. In LCA, economic and environmental flows as well as other data such as characterization factors or parameters may include uncertainty information (e.g. mathematical distributions or pedigree scores). During Monte Carlo simulation, random samples of this data are generated to calculate LCA results. 

In the Activity Browser, Monte Carlo Simulation can be used. The **steps **for this are:
1. To create a [calculation setup](https://github.com/LCA-ActivityBrowser/activity-browser/wiki#creating-a-calculation-setup) and perform a (static, i.e. non-stochastic) LCA. 
2. Then the user should go to the `Monte Carlo` tab
3. Then the following settings are available

* Here the users needs to specify the number of **iterations** (we recommend to start with at least 100). 
* A **random seed** can be determined, which can be used to reproduce the same random values again. 
* Finally, the user interface provides the option for **including or excluding uncertainty information** at the level of the technology matrix (technosphere), the interventions matrix (biosphere), the characterization factors, and parameters (if any have been defined by the practitioner). 

![Monte Carlo Simulation](https://user-images.githubusercontent.com/33026150/115353678-16e41480-a1b9-11eb-962e-9df0c7869d69.jpg)

An example for Monte Carlo Simulation results are shown below.

![Monte Carlo results](https://user-images.githubusercontent.com/33026150/115353677-16e41480-a1b9-11eb-8106-87f09b36991c.jpg)
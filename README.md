# Simulation Model

## Disclaimer

This repository is part of ongoing academic research. The source code for [PokerHandEvaluator](https://github.com/HenryRLee/PokerHandEvaluator) used in this repository is governed by its respective license. All rights are reserved for the remaining source code.

---

## The Model

This repository implements a stochastic game-theoretic model of human behavior in an incomplete information game (poker). The behavior modeled is non-deterministic, yet not entirely random, tending toward specific trends over the long term. A truncated normal distribution is utilized to simulate this behavior.

### Variables Involved

1. **$\bar{\mu}$**: A measure of how an entity perceives its current condition. It is calculated as:  
   $$\bar{\mu} = (1 + hs) \cdot ps$$  
   where:  
   - $hs$: Hand strength.  
   - $ps$: Pot share of the entity.  

2. **$ps$**: The portion of the pot an entity is expected to win based on its equity in the current hand. It is calculated as:  
   $$ps = \frac{\text{callValue}}{\text{pot}}$$  

3. **$ll$**: The lower limit of the truncated normal distribution, fixed at $0$.

4. **$ul'$**: The upper limit of an entity's playing range, determined as:  
   $$ul' = \begin{cases} sp + risk & \text{if } round \in \{1, 2\}; \\\\ hs + risk & \text{otherwise};\end{cases}$$  
   where:  
   - $sp$: Future potential.  
   - $risk$: The entity's risk appetite.
   - $round$: Poker game round (pre-flop for 0, flop for 1, so on).

5. **$ul$**: The actual upper limit of the truncated normal distribution, defined as:  
   $$ul = \max(\bar{\mu}, ul')$$  

### Truncated Normal Distribution

The truncated normal distribution is defined as:  
$$\psi(\bar{\mu}, \bar{\sigma}, ll, ul; x) = \begin{cases} 0 & x \leq ll; \\\\\frac{\phi(\bar{\mu}, \bar{\sigma}^2; x)}{\Phi(\bar{\mu}, \bar{\sigma}^2; ul) - \Phi(\bar{\mu}, \bar{\sigma}^2; ll)} & ll < x < ul; \\\\0 & x \geq ul.\end{cases}$$
where:  
- $\bar{\mu}$: Mean of the underlying normal distribution before truncation.  
- $\bar{\sigma}$: Standard deviation of the underlying normal distribution before truncation, calculated as $((ul - ll) / 3)$.  
- $ll$: Lower bound for truncation (fixed at $0$).  
- $ul$: Upper bound for truncation.  
- $x$: The random variable being evaluated.  
- $\phi(\bar{\mu}, \bar{\sigma}^2; x)$: Probability density function (PDF) of the normal distribution.  
- $\Phi(\bar{\mu}, \bar{\sigma}^2; a)$: Cumulative distribution function (CDF) of the normal distribution at $a$.

The PDF of the normal distribution is:  
$$\phi(x) = \frac{1}{\sqrt{2 \pi \bar{\sigma}^2}} e^{-\frac{(x - \bar{\mu})^2}{2 \bar{\sigma}^2}}$$  

The CDF is:  
$$\Phi(x) = \int_{-\infty}^x \phi(t) \, dt$$  

### Workflow Summary

After calculating the parameters of an entity's decision-making process, a decision factor is derived using the truncated normal distribution. This factor is then used to make a decision.

---

## Repository Components

| Folder         | Description                                                                 |
|----------------|-----------------------------------------------------------------------------|
| `analysis`     | Scripts for analyzing the output of the simulation engine.                 |
| `checks`       | Tests for various components of the engine.                                |
| `components`   | Core components of the simulation engine.                                  |
| `configs`      | Configuration files and generators for different game profiles.            |
| `data`         | Stores the output data generated by the simulation engine.                 |
| `engines`      | Variations of the simulation engines.                                      |
| `hand_evaluator` | Poker hand evaluation using [PokerHandEvaluator](https://github.com/HenryRLee/PokerHandEvaluator). |
| `poker_metrics` | Metrics to evaluate an entity's position in the poker game.               |
| `strategies`   | Player or strategy profiles.                                               |

**Note**: Detailed README files for each folder will be added in the future.

---

## Miscellaneous

### To-Do

- [x] clean up repository
  - [x] Remove chen from private value
  - [x] Decide whether to keep the rational .py files
  - [x] Clean up the batch configs
  - [x] Refactor codebase
    - [x] Refactor engine components
    - [x] Refactor Strategy
    - [x] Refactor poker_metrics
- [x] Decide something for the seed
- [x] clean up requirements.txt
- [x] create an all encompassing setup script that compiles shared library, creates virtual python environment and installs all dependencies
- [x] finalise all parameters (for strategies and others)
- [x] final code review
- [x] documentation (comments and other documentation for strategies)
- [x] change preflop betting
- [x] integrate risk into mean shifting
- [x] observe river
- [x] create optimal testing grounds for a more comprehensive testing
- [x] parameter evaluation demo
- [x] Bluffer limit implementation

### System Checks Before Final Simulation

- [x] Aggression factor displaying after end of simulation
- [x] Maths of strategy verified

### Run docker

Run `docker-compose up -d` to build and start container.
Local storage bounded, no need to build image again on code change.
Only rebuild in case of fundamental changes like changes to init.sh, requirements.txt, Dockerfile, etc.

To build image: `docker build . -t image_name`
To delete image: `docker image rm image_name`.

To run container: `docker run -di image_name`

To stop container: `docker stop container_hash`.
Get container hash using `docker ps`.
To delete container: `docker rm container_hash`.

NOTE: The building process might time out at times due to faulty connection or problems with debian repositories, just restart the building process.
NOTE: New files to poker_metrics/ and ./ should be manually added to the bind in docker-compose.yaml for it to be able to track it.

For docker hub:
To push:
`docker tag <name of the image> <dockerhub username>/<name of your repo>:<version>`
`docker push <tagged image name>:<version name>`

To pull:
`docker pull <tagged image name>:<version>`

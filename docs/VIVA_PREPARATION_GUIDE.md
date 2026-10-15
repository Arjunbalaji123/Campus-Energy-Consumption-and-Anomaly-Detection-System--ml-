# Viva Voce Examination & Defense Preparation Guide

**Project:** AI-Based Campus Energy Consumption and Anomaly Detection System  
**Institution:** Coimbatore Institute of Technology (CIT), Coimbatore  

---

## Table of Contents
1. [General Project & Architectural Questions](#1-general-project--architectural-questions)
2. [Data Preprocessing & Feature Engineering](#2-data-preprocessing--feature-engineering)
3. [Machine Learning: Random Forest Regressor](#3-machine-learning-random-forest-regressor)
4. [Anomaly Detection: Dual-Method Engine](#4-anomaly-detection-dual-method-engine)
5. [Deep Learning: LSTM Sequence Network vs. Traditional ML](#5-deep-learning-lstm-sequence-network-vs-traditional-ml)
6. [Explainability Engine & Prescriptive Recommendations](#6-explainability-engine--prescriptive-recommendations)
7. [Database Architecture & Backend Systems](#7-database-architecture--backend-systems)
8. [Frontend Architecture & Visualization](#8-frontend-architecture--visualization)

---

## 1. General Project & Architectural Questions

### Q1: What is the primary objective of this project?
**Answer:** The objective is to provide campus administrators, energy managers, and facilities engineers at CIT Coimbatore with an automated decision support system that:
1. Predicts dynamic expected electricity baselines based on building characteristics, operational schedules, and meteorological context.
2. Detects operational anomalies using both residual deviation analysis and unsupervised Isolation Forest.
3. Provides transparent, physical root-cause explanations rather than black-box alarms.
4. Prescribes role-assigned operational workflows with quantified financial savings in Indian Rupees (₹).

### Q2: Why is this system described as an "Academic Decision Support Prototype" rather than a real-time SCADA/BEMS controller?
**Answer:** In safety-critical campus infrastructure (high-voltage sub-stations, precision server rooms), automated control actions (such as remotely tripping breakers or altering chiller setpoints based on AI predictions) introduce significant operational risks. This prototype acts as an advisory decision support layer that highlights abnormal behaviors, quantifies energy waste, and presents evidence to human engineers who verify and execute the physical mitigation.

### Q3: How was academic integrity maintained regarding CIT's actual energy data?
**Answer:** Full-scale IoT smart sub-meters are not yet installed across all CIT blocks. To ensure complete academic transparency:
- Synthetic observations are marked with an explicit boolean flag (`is_synthetic = True`) and labeled with their source (`data_source = "synthetic_seed"`).
- Synthetic data was generated using thermodynamically validated formulas reflecting Coimbatore's microclimate (monsoon patterns, heatwaves) and CIT's academic calendar.
- Real observations entered by authorized users or imported via CSV are tracked separately and never mixed without explicit source indicators.

---

## 2. Data Preprocessing & Feature Engineering

### Q4: What is target leakage in time-series forecasting, and how did your pipeline prevent it?
**Answer:** Target leakage occurs when information from the future (or the test period) is inadvertently leaked into the training process, producing artificially inflated test scores that fail in production. We prevented leakage via two strict mechanisms:
1. **Strict Chronological Train/Test Split:** We avoided random shuffling (such as standard `train_test_split`). Instead, the dataset was sorted chronologically: the earliest 80% was assigned to training ($5,186$ rows) and the latest 20% to testing ($1,297$ rows).
2. **Frozen Training Imputation Parameters:** Missing value medians and scaling parameters (`StandardScaler`) were fitted *exclusively* on the training split, persisted to `preprocessor.joblib`, and applied downstream without re-computing on test observations.

### Q5: Why did you use cyclical sine and cosine transformations for hours and weekdays?
**Answer:** Standard integer representations of time (e.g., hour $0$ to $23$) introduce an artificial numerical discontinuity: hour $23$ (11:00 PM) and hour $0$ (12:00 AM) are adjacent in reality, but numerically separated by $23$ units. Linear and distance-based models would treat them as opposites.
By projecting hour onto a 2D trigonometric circle:
$$\text{hour\_sin} = \sin\left(\frac{2\pi \cdot \text{hour}}{24}\right), \quad \text{hour\_cos} = \cos\left(\frac{2\pi \cdot \text{hour}}{24}\right)$$
Hour $23$ and hour $0$ are placed right next to each other in Euclidean space, preserving smooth periodic continuity.

### Q6: How does the pipeline handle missing sensor records (e.g., unrecorded temperature or occupancy)?
**Answer:** We implemented a two-fold strategy:
1. Imputation: Missing values are filled with the frozen training median.
2. Missingness Indicators: Explicit boolean features (`is_temp_missing`, `is_occupancy_missing`) are appended to the feature vector.
This allows tree-based models like Random Forest to branch explicitly on the fact that a sensor was down, rather than mistaking an imputed median for an actual measured observation.

---

## 3. Machine Learning: Random Forest Regressor

### Q7: Why choose RandomForestRegressor over simple Linear Regression or Support Vector Regressor (SVR)?
**Answer:**
1. **Non-Linear Interactions:** Campus energy dynamics involve complex threshold interactions (e.g., air conditioning load spikes non-linearly only when ambient temperature exceeds $30^\circ\text{C}$ *and* occupancy is non-zero). Linear models cannot capture these interactions without manual polynomial expansion.
2. **Inherent Robustness to Outliers:** Unlike SVR or neural networks with Mean Squared Error loss that can be skewed by severe outliers, Random Forest's bootstrap aggregating (bagging) averages predictions across 120 randomized trees, dampening anomalous noise.
3. **Audit-Ready Interpretability:** Random Forest natively outputs Gini Impurity feature importance, allowing facilities engineers to verify which physical drivers (occupancy, building area, weather) govern predictions.

### Q8: What were your Random Forest hyperparameters, and how did it perform on unseen test data?
**Answer:**
- Hyperparameters: $N_{\text{estimators}} = 120$, $\text{max\_depth} = 16$, $\text{min\_samples\_split} = 4$, $\text{n\_jobs} = -1$.
- Performance on held-out test split:
  - $R^2 = 0.9720$ (explaining $97.20\%$ of energy variance).
  - $\text{MAE} = 2.25\text{ kWh}$.
  - $\text{RMSE} = 3.82\text{ kWh}$.

### Q9: What were the top predictive features identified by Random Forest?
**Answer:**
1. Occupancy Ratio: $69.95\%$ (human presence and associated lighting/PC usage is the primary driver of institutional power).
2. IT Computer Center Category: $17.51\%$ (precision cooling and continuous server infrastructure create elevated baselines).
3. Laboratory Block Category: $4.17\%$ (specialized instrumentation and laboratory exhaust hoods).
4. HVAC Availability: $2.57\%$ (air conditioning versus natural ventilation).
5. Outdoor Temperature: $1.39\%$ (ambient thermal cooling load).

---

## 4. Anomaly Detection: Dual-Method Engine

### Q10: What is the dual-method anomaly detection architecture, and why is a single method insufficient?
**Answer:** A single anomaly detection technique exhibits systematic blind spots:
- **Residual Analysis** compares actual consumption to expected baseline ($E_{\text{actual}} - E_{\text{expected}}$). While excellent for single-variable spikes, it depends heavily on model prediction accuracy and can be confused if the predictor overfits.
- **Isolation Forest** is an unsupervised multi-dimensional algorithm that isolates points by recursive random partitioning. It excels at detecting unusual combinations of features (e.g., high power when occupancy is near zero) without requiring labeled training data, but does not quantify exact kilowatt-hour excess.

By running both algorithms concurrently, our system highlights **Dual-Method Confirmed Anomalies** where both independent paradigms agree, dramatically reducing false alarm rates.

### Q11: How does Isolation Forest mathematically isolate anomalies?
**Answer:** Isolation Forest isolates anomalies by randomly selecting a feature and a random split value between that feature's minimum and maximum. Because anomalies are "few and different", they lie in sparse regions of the multi-dimensional space and require significantly fewer recursive splits to be isolated in a leaf node.
The anomaly score $s(x, n)$ is defined as:
$$s(x, n) = 2^{-\frac{\mathbb{E}(h(x))}{c(n)}}$$
where $h(x)$ is the path length (number of edges traversed from root to leaf), $\mathbb{E}(h(x))$ is the average path length across all 150 trees, and $c(n)$ is the average path length of unsuccessful searches in a Binary Search Tree (BST) with $n$ nodes:
$$c(n) = 2\left(\ln(n - 1) + 0.5772156649\right) - \frac{2(n - 1)}{n}$$
- If $\mathbb{E}(h(x)) \to 0$, $s \to 1$ (Definite Anomaly).
- If $\mathbb{E}(h(x)) \to n - 1$, $s \to 0$ (Normal Inlier).

### Q12: Why is an anomaly score NOT a probability of a physical equipment fault?
**Answer:** An anomaly score is a measure of statistical rarity in a feature distribution, not an engineering diagnosis. A high anomaly score simply indicates that an observation deviates significantly from historical patterns. For example, a sudden campus symposium or hackathon on a Saturday night generates an unusual energy spike that is statistically anomalous, yet operationally legitimate. This distinction is why our system pairs anomaly detection with transparent physical explainability rules.

---

## 5. Deep Learning: LSTM Sequence Network vs. Traditional ML

### Q13: Describe your LSTM neural network architecture.
**Answer:** The LSTM model is formulated as a temporal sequence regressor receiving a 24-hour sliding window ($L = 24$, $D = 8$ features per timestep) to predict the energy consumption at hour $t$:
- Input shape: $(B, 24, 8)$ where features include lagged consumption, cyclical hour sin/cos, weekday sin/cos, outdoor temperature, occupancy ratio, and building floor area.
- LSTM Hidden Layer: $H = 32$ hidden units with combined gate weight matrices ($W \in \mathbb{R}^{8 \times 128}$, $U \in \mathbb{R}^{32 \times 128}$, $b \in \mathbb{R}^{128}$).
- Gates: Forget gate ($f_t$), Input gate ($i_t$), Candidate cell ($\tilde{c}_t$), Output gate ($o_t$).
- Output Linear Projection: $W_y \in \mathbb{R}^{32 \times 1}, b_y \in \mathbb{R}^{1}$ projecting the final hidden state $h_{24}$ to scalar kilowatt-hour prediction.
- Optimization: Backpropagation Through Time (BPTT) with Adam optimizer ($\eta = 0.005$, $\beta_1 = 0.9, \beta_2 = 0.999$, $\epsilon = 10^{-8}$) and gradient clipping $[-5.0, 5.0]$.

### Q14: How does an LSTM cell solve the vanishing gradient problem encountered in standard RNNs?
**Answer:** In standard Recurrent Neural Networks (RNNs), gradients backpropagated through time are repeatedly multiplied by recurrent weight matrices $W_h^T$. Over long sequences ($L \ge 24$), this repeated product causes gradients to exponentially decay to zero (vanishing gradient) or explode.
LSTMs solve this by introducing an additive **Constant Error Carousel (CEC)** represented by the cell state $c_t$:
$$c_t = f_t \odot c_{t-1} + i_t \odot \tilde{c}_t$$
The derivative of the cell state with respect to the previous cell state contains an additive term:
$$\frac{\partial c_t}{\partial c_{t-1}} = f_t$$
If the forget gate $f_t$ is close to $1.0$, gradients can flow back across arbitrary time horizons without exponential decay.

### Q15: Why did Random Forest ($R^2=0.9720$) outperform/match LSTM ($R^2=0.9304$), and why is Random Forest preferred for production deployment here?
**Answer:**
1. **Single-Observation Manual Entry:** In an administrative dashboard where users manually log a single meter reading, Random Forest predicts immediately from that one row. An LSTM requires a continuous buffer of the preceding 24 hours of telemetry, making single-reading manual entry operationally difficult.
2. **Missing Context Handling:** Campus telemetry often has gaps in weather or occupancy records. Random Forest branches on missing indicator flags naturally, whereas LSTMs require continuous temporal imputation.
3. **Interpretability:** Random Forest provides transparent Gini feature importance (e.g. Occupancy 70%, IT Block 17.5%), whereas LSTM gate activations ($f_t, i_t, o_t$) are black-box mechanisms that cannot be readily audited by non-ML electrical engineers.
4. **Compute Footprint:** Random Forest trains in $1.45\text{ seconds}$ on standard CPU, compared to $9.54\text{ seconds}$ for LSTM.

---

## 6. Explainability Engine & Prescriptive Recommendations

### Q16: How does the Rule-Based Explainability Engine prevent AI hallucinations?
**Answer:** Large Language Models (LLMs) often hallucinate plausible-sounding but unverified physical causes. Our system implements a deterministic, rule-based expert engine that inspects exact numeric thresholds from the observation:
- **Nighttime Lighting / HVAC Surge:** Triggered only if $\text{hour} \in [21, 5]$, $\text{occupancy} \le 10$, and $\text{residual} > +15\text{ kWh}$.
- **Chiller Degradation / High Daytime Load:** Triggered only if $\text{hour} \in [9, 17]$, $\text{residual} > +20\text{ kWh}$, and building has HVAC.
- **Sub-Station Telemetry Drop:** Triggered only if $\text{energy} < 5\text{ kWh}$ during normal operating hours.

Because each rule evaluates concrete boolean propositions on verified database columns, the generated hypotheses and confidence ratings are deterministic, reproducible, and verifiable.

### Q17: How are operational recommendations linked to financial savings?
**Answer:** Recommendations calculate estimated kilowatt-hour reductions based on the observed residual deviation:
$$\text{Estimated Savings (kWh)} = \text{Actual kWh} - \text{Expected Baseline kWh}$$
To make these savings actionable for administrative decision-makers, they are converted into Indian Rupees (₹) using Coimbatore's institutional commercial electricity tariff ($₹7.50/\text{kWh}$):
$$\text{Cost Reduction Potential (₹)} = \text{Estimated Savings (kWh)} \times ₹7.50$$
Specific directives are assigned to designated campus operational roles (Campus Electrical Supervisor, HVAC Facilities Technician, Estate Officer).

---

## 7. Database Architecture & Backend Systems

### Q18: What is the database design, and how does the system support both PostgreSQL and local SQLite?
**Answer:** The database schema is fully normalized into 11 relational entities with primary keys, foreign key constraints, cascade deletion policies, and indexing on frequent lookup columns (`timestamp`, `building_id`, `severity`, `status`).
In [`backend/app/core/config.py`](file:///home/Arjun/Desktop/ml%20lab/ml%20project/backend/app/core/config.py), the system dynamically detects the database driver:
- If a production PostgreSQL instance is configured (`postgresql+psycopg2://...`), it connects natively.
- If PostgreSQL is unavailable, it automatically falls back to an absolute-path local SQLite database (`backend/cit_energy.db`) without code modifications, ensuring seamless portability during viva demonstrations.

### Q19: What is Alembic, and why is it used for database migrations?
**Answer:** Alembic is SQLAlchemy's lightweight database migration tool. As a software prototype evolves, database tables, column types, and constraints change. Rather than manually dropping and recreating tables (which destroys existing campus observations), Alembic records incremental, version-controlled migration scripts (`alembic upgrade head`), allowing reproducible schema evolution across development and production environments.

---

## 8. Frontend Architecture & Visualization

### Q20: Why choose React 19, TypeScript, and Vite over traditional server-rendered templates (e.g., Jinja2)?
**Answer:**
1. **Real-Time Client-Side Interactivity:** React's component state model enables dynamic client-side interactions (e.g. toggling buildings, adjusting time horizons between 7d/14d/30d, filtering anomaly severities) without full-page reloads.
2. **Type Safety & Schema Synchronization:** TypeScript interfaces mirror backend Pydantic models with `verbatimModuleSyntax: true`, catching API mismatch bugs at compile-time before deployment.
3. **Fast Bundling:** Vite leverages native ES modules during development, providing instant Hot Module Replacement (HMR) and fast production builds.

### Q21: What visualizations were implemented with Recharts, and what operational insights do they provide?
**Answer:**
1. **Actual vs Expected Baseline Area/Line Chart:** Renders actual observed consumption in shaded indigo, expected baseline as a dashed emerald line, and flagged anomalies as high-contrast red markers with tooltips.
2. **24-Hour Diurnal Load Profile:** Compares working day load curves (steep daytime ramp peaking at ~65 kWh) against weekend standby baseload (~22 kWh), exposing after-hours baseload leakage.
3. **Campus Facilities Consumption Bar Chart:** Compares total kWh and average hourly loads across campus buildings with category color coding.
4. **Anomaly Severity Donut Chart:** Visualizes Critical vs. Warning vs. Normal distribution.


# AirAds User Roles & Responsibilities

**Version: 1.0**  
**Date: February 2026**  
**Status: Complete Documentation**

---

## **Overview**

AirAds implements a comprehensive Role-Based Access Control (RBAC) system with **11 distinct roles** designed to ensure scalable operations, maintain platform quality, and provide proper governance. The roles are divided into two categories:

- **Phase-A Data Collection Roles (7 roles)**: Original roles for core platform operations
- **Governance Roles (4 roles)**: Added for Phase-1 administrative operations

---

## **Phase-A Data Collection Roles**

### **1. SUPER_ADMIN**

**Role Level**: Highest authority  
**Primary Purpose**: Platform governance and emergency management

**Responsibilities**:
- Full platform control and system configuration
- Role management and user access administration
- Emergency response for critical incidents
- System-level changes and deployments
- Legal compliance oversight
- Final escalation point for disputes

**System Access**:
- ✅ All systems and data
- ✅ User management tools
- ✅ System configuration panels
- ✅ Analytics dashboards (read/write)
- ✅ Vendor suspension capabilities

**Why AirAds Needs This Role**:
- Ultimate authority for platform governance
- Emergency response capabilities
- System integrity and security management
- Legal and compliance final decisions

---

### **2. CITY_MANAGER**

**Role Level**: Regional authority  
**Primary Purpose**: Geographic area oversight and local market health

**Responsibilities**:
- Manage platform operations within assigned city/region
- Oversee local vendor verification processes
- Monitor regional platform health metrics
- Coordinate field agents and local support staff
- Handle city-specific escalations
- Local market analysis and reporting

**System Access**:
- ✅ Vendor dashboard (city-filtered view)
- ✅ Moderation queue (local items)
- ✅ Regional analytics dashboards
- ✅ Field agent coordination tools
- ❌ System configuration
- ❌ Cross-city data access

**Why AirAds Needs This Role**:
- Enables geographic scaling of operations
- Provides local market expertise
- Ensures region-specific quality control
- Manages local vendor relationships

---

### **3. DATA_ENTRY**

**Role Level**: Operational staff  
**Primary Purpose**: Manual data collection and entry

**Responsibilities**:
- Manual data input when automated sources are insufficient
- Vendor information updates and corrections
- Basic data cleanup and normalization
- Process data from external sources (documents, forms)
- Validate data format and completeness
- Flag suspicious data for review

**System Access**:
- ✅ Data entry forms and interfaces
- ✅ Vendor profile editing (basic fields)
- ✅ Data validation tools
- ✅ Bulk import utilities
- ❌ Deletion capabilities
- ❌ Sensitive data access

**Why AirAds Needs This Role**:
- Handles edge cases where automation fails
- Ensures data completeness
- Supports vendor onboarding process
- Maintains data quality standards

---

### **4. QA_REVIEWER**

**Role Level**: Quality control  
**Primary Purpose**: Quality assurance and audit processes

**Responsibilities**:
- Review and validate data entered by DATA_ENTRY staff
- Conduct regular quality audits on platform data
- Verify vendor information accuracy
- Check compliance with data standards
- Identify and flag quality issues
- Generate quality reports and metrics

**System Access**:
- ✅ Review queues and audit tools
- ✅ Data quality dashboards
- ✅ Validation check interfaces
- ✅ Reporting and analytics tools
- ❌ Direct data editing (review-only)
- ❌ User management

**Why AirAds Needs This Role**:
- Ensures platform data quality
- Prevents errors from reaching production
- Maintains user trust through accuracy
- Supports compliance requirements

---

### **5. FIELD_AGENT**

**Role Level**: On-site verification  
**Primary Purpose**: Physical business verification and ground-truth data collection

**Responsibilities**:
- On-site business verification when remote methods fail
- GPS coordinate validation and correction
- Photo and video collection for vendor profiles
- Physical business location confirmation
- Document collection (business licenses, permits)
- Report field observations and anomalies

**System Access**:
- ✅ Mobile field verification tools
- ✅ GPS validation interfaces
- ✅ Photo/video upload capabilities
- ✅ Field reporting forms
- ❌ Sensitive vendor data
- ❌ System configuration

**Why AirAds Needs This Role**:
- Provides ground-truth verification
- Handles cases where remote verification fails
- Ensures physical business existence
- Supports fraud prevention

---

### **6. ANALYST**

**Role Level**: Business intelligence  
**Primary Purpose**: Data analysis and insights generation

**Responsibilities**:
- Analyze platform performance metrics
- Generate business insights and recommendations
- Create reports for management and stakeholders
- Identify trends and patterns in user behavior
- Support strategic decision-making with data
- Conduct ad-hoc analysis for special projects

**System Access**:
- ✅ Analytics dashboards and tools
- ✅ Data export and analysis interfaces
- ✅ Report generation capabilities
- ✅ Business intelligence tools
- ❌ Raw PII data (aggregated only)
- ❌ System administration

**Why AirAds Needs This Role**:
- Provides data-driven decision support
- Identifies growth opportunities
- Monitors platform health
- Supports strategic planning

---

### **7. SUPPORT**

**Role Level**: Customer service  
**Primary Purpose**: User and vendor assistance

**Responsibilities**:
- Handle user and vendor support tickets
- Provide basic troubleshooting and guidance
- Assist with account setup and onboarding
- Answer platform usage questions
- Escalate complex issues to appropriate teams
- Document common issues and solutions

**System Access**:
- ✅ Support CRM and ticketing system
- ✅ Read-only vendor profiles
- ✅ Knowledge base and help documentation
- ✅ Communication tools (email, chat)
- ❌ Sensitive user data beyond support context
- ❌ System modification capabilities

**Why AirAds Needs This Role**:
- Front-line assistance for platform users
- Reduces friction in user experience
- Collects user feedback and issues
- Prevents escalation of simple problems

---

## **Governance Roles (Phase-1 Addition)**

### **8. OPERATIONS_MANAGER**

**Role Level**: Operations leadership  
**Primary Purpose**: Day-to-day operations management and team coordination

**Responsibilities**:
- Oversee vendor verification workflows
- Handle complex escalations and disputes
- Coordinate content moderation and quality teams
- Monitor operational SLAs and metrics
- Manage team schedules and workload distribution
- Implement process improvements

**System Access**:
- ✅ Vendor verification dashboard
- ✅ Moderation queue management
- ✅ Team performance analytics
- ✅ Escalation handling tools
- ✅ Vendor suspension capabilities
- ❌ System configuration

**Why AirAds Needs This Role**:
- Ensures smooth daily operations
- Provides escalation point for complex issues
- Maintains team productivity and quality
- Implements operational improvements

---

### **9. CONTENT_MODERATOR**

**Role Level**: Content safety  
**Primary Purpose**: Content quality and safety enforcement

**Responsibilities**:
- Review flagged reels and promotional content
- Enforce content policies and community standards
- Validate promotional offers and discounts
- Screen vendor profiles for inappropriate content
- Handle user-reported content issues
- Document moderation decisions and patterns

**System Access**:
- ✅ Content moderation dashboard
- ✅ Vendor profile screening tools
- ✅ Promotion validation interfaces
- ✅ User report management
- ❌ Vendor suspension (escalates to Ops Manager)
- ❌ System analytics beyond content metrics

**Why AirAds Needs This Role**:
- Maintains platform safety and quality
- Prevents harmful or misleading content
- Ensures promotional integrity
- Protects user experience

---

### **10. DATA_QUALITY_ANALYST**

**Role Level**: Data integrity  
**Primary Purpose**: Tag accuracy, GPS validation, and data cleanup

**Responsibilities**:
- Conduct monthly tag accuracy audits
- Validate GPS coordinates and detect drift
- Manage and maintain tag taxonomy
- Perform data cleanup and normalization
- Identify and correct systematic data issues
- Propose taxonomy improvements

**System Access**:
- ✅ Data management and cleanup tools
- ✅ Tag taxonomy editor
- ✅ GPS validation interfaces
- ✅ Quality audit dashboards
- ✅ Analytics for data quality metrics
- ❌ Vendor suspension capabilities

**Why AirAds Needs This Role**:
- Maintains data accuracy and integrity
- Ensures proper categorization and tagging
- Supports search and discovery functionality
- Prevents data quality degradation

---

### **11. ANALYTICS_OBSERVER**

**Role Level**: Monitoring and reporting  
**Primary Purpose**: Platform health monitoring (read-only)

**Responsibilities**:
- Monitor platform health metrics and KPIs
- Generate regular operational reports
- Track performance against targets
- Identify trends requiring attention
- Provide insights to leadership teams
- Document platform performance history

**System Access**:
- ✅ Analytics dashboards (read-only)
- ✅ Performance monitoring tools
- ✅ Report generation and export
- ✅ Historical data access
- ❌ Any write or modification capabilities
- ❌ Sensitive user data access

**Why AirAds Needs This Role**:
- Provides unbiased platform monitoring
- Ensures transparency in operations
- Supports data-driven decision making
- Maintains performance accountability

---

## **Access Control Matrix**

| **System Component**           | **Super Admin** | **City Manager** | **Data Entry** | **QA Reviewer** | **Field Agent** | **Analyst** | **Support** | **Ops Manager** | **Content Moderator** | **Data Quality Analyst** | **Analytics Observer** |
|--------------------------------|-----------------|------------------|----------------|-----------------|-----------------|-------------|-------------|-----------------|----------------------|---------------------------|-----------------------|
| Vendor Verification Queue      | ✅              | ✅               | ❌            | ❌              | ❌              | ❌          | ❌          | ✅              | ❌                   | ❌                        | ❌                    |
| Content Moderation Dashboard   | ✅              | ✅               | ❌            | ❌              | ❌              | ❌          | ❌          | ✅              | ✅                   | ❌                        | ❌                    |
| Tag Taxonomy Editor            | ✅              | ❌               | ❌            | ❌              | ❌              | ❌          | ❌          | ❌              | ❌                   | ✅                        | ❌                    |
| User Data Access               | ✅              | ❌               | ❌            | ❌              | ❌              | ❌          | Limited     | ❌              | ❌                   | ❌                        | Anonymized            |
| Vendor Suspension Actions      | ✅              | ✅               | ❌            | ❌              | ❌              | ❌          | ❌          | ✅              | ❌                   | ❌                        | ❌                    |
| Analytics Dashboards           | ✅              | ✅               | ❌            | ✅              | ❌              | ✅          | Read-only   | ✅              | Read-only           | ✅                        | ✅                    |
| System Configuration           | ✅              | ❌               | ❌            | ❌              | ❌              | ❌          | ❌          | ❌              | ❌                   | ❌                        | ❌                    |
| Field Operations Tools         | ✅              | ✅               | ❌            | ❌              | ✅              | ❌          | ❌          | ❌              | ❌                   | ❌                        | ❌                    |

---

## **Role Hierarchy & Escalation Paths**

### **Escalation Matrix**

| **Issue Type**                 | **First Line**        | **Escalation Level 1** | **Escalation Level 2** |
|--------------------------------|-----------------------|------------------------|------------------------|
| Vendor Claim Dispute           | Support Agent         | Operations Manager     | Super Admin            |
| Content Moderation Appeal      | Content Moderator     | Operations Manager     | Legal Team             |
| Data Quality Issues            | Data Quality Analyst  | Operations Manager     | Super Admin            |
| Technical Platform Issues      | Support Agent         | Engineering Team       | CTO                    |
| Fraud Investigation            | Data Analyst          | Operations Manager     | Super Admin + Legal    |
| User Privacy Complaint         | Support Agent         | Compliance Officer     | Legal Team             |

### **Decision Authority Levels**

**Level 1 - Immediate Action**:
- Content Moderator: Content removal, warnings
- Data Quality Analyst: Tag corrections, data cleanup
- Support Agent: Basic account assistance

**Level 2 - Supervisory Approval**:
- Operations Manager: Vendor suspensions, policy exceptions
- City Manager: Regional operational decisions
- QA Reviewer: Quality standards enforcement

**Level 3 - Executive Authority**:
- Super Admin: System changes, role modifications, legal compliance
- Legal Team: Legal disputes, regulatory compliance

---

## **Why AirAds Needs This Role Structure**

### **1. Scalable Operations**
- **Automation + Human Oversight**: 70% automated verification, 30% manual review
- **Specialization**: Each role handles specific aspects efficiently
- **24/7 Coverage**: Multiple roles enable shift-based operations
- **Geographic Scaling**: City Managers enable regional expansion

### **2. Quality & Safety**
- **Content Moderation**: Prevents harmful, misleading, or illegal content
- **Fraud Prevention**: Multi-layer detection and prevention system
- **Data Integrity**: Continuous validation and correction processes
- **User Protection**: Safety mechanisms and enforcement policies

### **3. Vendor Management**
- **Verification Workflow**: OTP + manual review for business claims
- **Support Structure**: Tiered support from basic to complex issues
- **Quality Control**: Regular audits and maintenance of standards
- **Relationship Management**: Professional vendor interactions

### **4. Compliance & Governance**
- **Audit Trail**: Complete logging of all administrative actions
- **GDPR Compliance**: Data subject rights and privacy protection
- **Policy Enforcement**: Clear rules and consistent application
- **Legal Protection**: Proper documentation and processes

### **5. Platform Health**
- **Analytics Monitoring**: Real-time performance tracking
- **Incident Response**: Defined roles for emergency situations
- **Continuous Improvement**: Data-driven optimization
- **Risk Management**: Proactive issue identification

### **6. Business Intelligence**
- **Strategic Insights**: Data supports business decisions
- **Performance Tracking**: KPI monitoring and reporting
- **Market Analysis**: Regional and trend analysis
- **Growth Planning**: Informed expansion strategies

---

## **Implementation Notes**

### **Technical Implementation**
- **RBAC System**: Role-based permissions enforced at API level
- **Audit Logging**: All actions logged with timestamps and user IDs
- **Session Management**: Secure authentication and authorization
- **Data Access Controls**: Field-level encryption and access restrictions

### **Operational Guidelines**
- **SLAs**: Defined response times for each role type
- **Training**: Role-specific onboarding and continuous education
- **Performance Metrics**: KPIs for role effectiveness
- **Quality Assurance**: Regular audits and calibration sessions

### **Future Scalability**
- **Role Evolution**: Roles can be added or modified as platform grows
- **Automation Integration**: Roles will evolve with increased automation
- **Regional Adaptation**: Roles can be customized for different markets
- **Compliance Updates**: Roles adapt to changing regulatory requirements

---

## **Conclusion**

The AirAds role structure provides a comprehensive framework for platform governance that balances automation with human oversight, ensures quality and safety, maintains compliance, and enables scalable growth. Each role serves a specific purpose in the platform's ecosystem, working together to create a trusted and reliable marketplace for vendors and users.

**Success depends on**:
1. **Clear Role Definitions**: Well-documented responsibilities and access levels
2. **Proper Training**: Role-specific onboarding and continuous education  
3. **Effective Coordination**: Clear communication and escalation paths
4. **Continuous Improvement**: Regular review and optimization of processes
5. **Strong Governance**: Consistent policy enforcement and audit compliance

---

**Document Version**: 1.0  
**Last Updated**: February 2026  
**Next Review**: June 2026  
**Maintained By**: Operations Team

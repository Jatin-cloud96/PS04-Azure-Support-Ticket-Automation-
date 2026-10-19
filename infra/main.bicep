// Azure Bicep Infrastructure-as-Code Template
// Provisions Serverless Azure Function App, Storage Account, Containers, and Application Insights
// for PS03 Azure Invoice Processing Pipeline

@description('Azure Region for resource deployment')
param location string = resourceGroup().location

@description('Environment prefix (e.g. dev, test, prod)')
param environment string = 'prod'

@description('Unique suffix for globally unique resource names')
param uniqueSuffix string = uniqueString(resourceGroup().id)

var storageAccountName = 'stcerevyn${environment}${take(uniqueSuffix, 8)}'
var appServicePlanName = 'plan-cerevyn-invoices-${environment}'
var functionAppName = 'func-cerevyn-invoices-${environment}-${take(uniqueSuffix, 6)}'
var logAnalyticsName = 'log-cerevyn-${environment}'
var appInsightsName = 'appi-cerevyn-invoices-${environment}'

// 1. Log Analytics Workspace
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: logAnalyticsName
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

// 2. Application Insights
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

// 3. Azure Storage Account (General Purpose v2)
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    supportsHttpsTrafficOnly: true
    accessTier: 'Hot'
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
  }
}

// 4. Blob Service & Partitioned Containers
resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  parent: storageAccount
  name: 'default'
  properties: {
    deleteRetentionPolicy: {
      enabled: true
      days: 7
    }
  }
}

var containerNames = [
  'invoices-input'
  'invoices-output'
  'invoices-review'
  'invoices-failed'
  'invoices-hashes'
]

resource containers 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = [for name in containerNames: {
  parent: blobService
  name: name
  properties: {
    publicAccess: 'None'
  }
}]

// 5. Azure App Service Plan (Linux Consumption Plan - Scale to Zero)
resource appServicePlan 'Microsoft.Web/serverfarms@2022-09-01' = {
  name: appServicePlanName
  location: location
  sku: {
    name: 'Y1'
    tier: 'Dynamic'
  }
  properties: {
    reserved: true // Required for Linux
  }
}

// 6. Azure Function App (Python 3.11 with System-Assigned Managed Identity)
resource functionApp 'Microsoft.Web/sites@2022-09-01' = {
  name: functionAppName
  location: location
  kind: 'functionapp,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: appServicePlan.id
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.11'
      appSettings: [
        {
          name: 'AzureWebJobsStorage'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};EndpointSuffix=${environment().suffixes.storage};AccountKey=${storageAccount.listKeys().keys[0].value}'
        }
        {
          name: 'FUNCTIONS_EXTENSION_VERSION'
          value: '~4'
        }
        {
          name: 'FUNCTIONS_WORKER_RUNTIME'
          value: 'python'
        }
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: appInsights.properties.ConnectionString
        }
        {
          name: 'INPUT_CONTAINER'
          value: 'invoices-input'
        }
        {
          name: 'OUTPUT_CONTAINER'
          value: 'invoices-output'
        }
        {
          name: 'REVIEW_CONTAINER'
          value: 'invoices-review'
        }
        {
          name: 'FAILED_CONTAINER'
          value: 'invoices-failed'
        }
        {
          name: 'CONFIDENCE_THRESHOLD'
          value: '0.70'
        }
      ]
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
    }
    httpsOnly: true
  }
}

// 7. Role Assignment: Storage Blob Data Contributor to Function App Managed Identity
var storageBlobDataContributorRoleId = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'

resource roleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, functionApp.id, storageBlobDataContributorRoleId)
  scope: storageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageBlobDataContributorRoleId)
    principalId: functionApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

output storageAccountName string = storageAccount.name
output functionAppName string = functionApp.name
output functionAppPrincipalId string = functionApp.identity.principalId
output appInsightsConnectionString string = appInsights.properties.ConnectionString

# WebClerk2 Utilities, Features, and Functions

This document lists the utilities, features, and functions harvested from WebClerk2 (4D versions) located in `/Users/williamjames/Documents/CommerceExpert/000_webclerk_ai_training/WebClerk20_zzz/Methods/`.

These are categorized by directory and need to be transferred or rewritten one at a time to account for schema changes in WebClerk3 (Django).

## Schema Mapping: WebClerk2 Tables to WebClerk3 Models

To facilitate transfer/rewrite, here's a mapping of common WebClerk2 table names to current WebClerk3 Django models. This helps identify existing equivalents and avoid duplicates.

| WebClerk2 Table | WebClerk3 Model | Location |
|-----------------|-----------------|----------|
| Customers | Customer | `apps/orgs/models/base_org_model.py` |
| Contacts | Contact | `apps/core/models/contact.py` |
| Orders | SalesOrder | `apps/transactions/models/sales_order.py` |
| OrderLines | SalesOrderLine | `apps/transactions/models/sales_order.py` |
| Items/Products | Item | `apps/products/models/item.py` |
| Invoices | Invoice | `apps/accounts/models/invoice.py` (if exists) |
| Payments | Payment | `apps/transactions/models/payment.py` |
| GL Accounts | GLAccount | `apps/accounts/models/gl_account.py` |
| Journals | GLJournal | `apps/accounts/models/gl_journal.py` |
| Vendors/Suppliers | Vendor | `apps/orgs/models/base_org_model.py` (likely Customer with type) |
| Employees | Employee | `apps/orgs/models/base_org_model.py` (likely Customer with type) |
| Settings | Setting | `apps/core/models/setting.py` |
| Actions | Action | `apps/core/models/action.py` |
| Notifications | Notification | `apps/core/models/notification.py` |
| Templates | Template | `apps/core/models/template.py` |
| Reports | Report | `apps/core/models/report.py` |
| Documents | Document | `apps/docs/models/document.py` |
| Tags | Tag | `apps/docs/models/tag.py` |
| Warehouses | Warehouse | `apps/products/models/warehouse.py` |
| Inventory | InventoryLayer, InventoryReservation, etc. | `apps/products/models/` |

**Notes:**

- Many entities are unified under `Customer` in WebClerk3 with types (customer, vendor, employee).
- Check existing models before creating new ones.
- Use this mapping when reading 4D code to translate table references.

## Categories Overview

- **Qx**: 158 methods
- **HTTP**: 127 methods
- **zzz**: 37 methods
- **HTML**: 29 methods
- **EDI**: 20 methods
- **Print**: 17 methods
- **CMA**: 17 methods
- **j**: 15 methods
- **B2B**: 12 methods
- **Word**: 8 methods
- **BarCode**: 7 methods
- **custom**: 5 methods
- **WC**: 4 methods
- **HO**: 4 methods
- **Utility**: 1 method
- Loose files: FormEventOnHeader.4dm, SRE_Print.4dm, URpt_SetUpPreview.4dm, UserReport_iloProcedure.4dm

## Detailed Lists

### EDI (20 methods)  -- outdated

- EDI_Bill3rdParty.4dm
- EDI_CheckOrder.4dm
- EDI_DecConst.4dm
- EDI_DupPONum.4dm
- EDI_Header.4dm
- EDI_InTestFiles.4dm
- EDI_OrdCancel.4dm
- EDI_OrdLnAddComplete.4dm
- EDI_OrdLnDupCheck.4dm
- EDI_OrdOpen.4dm
- EDI_OutMakeFile.4dm
- EDI_PackInvoice.4dm
- EDI_PackOrder_Client.4dm
- EDI_PackOrder_Server.4dm
- EDI_PackOrder.4dm
- EDI_ShipVia_LTL.4dm
- EDI_ShowAll.4dm
- EDI_StopOrder.4dm
- EDI_Trailer.4dm
- EDIParseReport.4dm

### WC (4 methods)  -- review

- 222_CatalogJava.4dm
- RelateOnWeb.4dm
- WCItemQuery.4dm
- WCItemQueryJim.4dm

### HTML (29 methods)  -- outdated from old server

- BootStrapConvert.4dm
- HTML_BuildOptions.4dm
- HTML_CheckSiteVars.4dm
- HTML_ConvertInputs.4dm
- Html_EditParse.4dm
- Html_ImagesByXWide.4dm
- HTML_jitTags2javaOK.4dm
- HTML_LineItemCatalog.4dm
- html_link.4dm
- HTML_MetaTagWrite.4dm
- HTML_ParseBody.4dm
- HTML_ParseJitVar.4dm
- HTML_ReplaceHead.4dm
- HTML_SelectWrite.4dm
- HTML_TagCheckPage.4dm
- HTML_TagClip.4dm
- HTML_TagFieldName.4dm
- Html_TagMetaJIT.4dm
- HTML_TabularTable.4dm
- HTML_UpDateObjects.4dm
- Html_URL_Draft.4dm
- Html_UrlFill.4dm
- HTML_URLItemKeywords.4dm
- Html_URLItemPage.4dm
- Html_URLSupportPage.4dm
- HTMLCleaner.4dm
- HtmlMenuMaker.4dm
- HTMLMetaTags.4dm
- HTMLPageHeadMake.4dm

### Print (17 methods)   -- outdated

- P_AddressesCustomer.4dm
- P_ClearHeadVars.4dm
- P_ClearUserVars.4dm
- P_CountLinesToPrint.4dm
- P_InvcLines.4dm
- P_ListVarRays.4dm
- P_Old_ToP_VarsHeader.4dm
- P_OrdHeader.4dm
- P_OrdLines.4dm
- P_PoHeader.4dm
- P_PoLines.4dm
- P_PpHeader.4dm
- P_PpLines.4dm
- P_Search.4dm
- P_SetReps.4dm
- PrintInvoiceLines.4dm
- PrintOrderLines.4dm

### B2B (12 methods)  -- sync outline

- B2B_Exchange.4dm
- B2B_Server.4dm
- B2BItemPack.4dm
- B2BItemsAsk.4dm
- B2BItemsSend.4dm
- B2BPOStatusGet.4dm
- B2BRecordAsk.4dm
- B2BRecordGet.4dm
- B2BRecordSend.4dm
- B2BRequests.4dm
- B2BSycnAvailable.4dm
- B2BSyncRequest.4dm

### BarCode (7 methods)  -- replace with qr and barcode external

- BarC_Fill.4dm
- BarC_MultiLabel.4dm
- Barcode_AssignLength.4dm
- BarcodeArray128Setup.4dm
- BarCodeBuild.4dm
- BarcodeGSCZip.4dm
- BarcodeSSCC.4dm

### CMA (17 methods)  -- outdated

- CMA_AbbotExport.4dm
- CMA_Comm_SrchOpts.4dm
- CMA_CustomerID.4dm
- CMA_ImportBefore.4dm
- CMA_ImportDuring.4dm
- CMA_ImportOrdLines.4dm
- CMA_ImportSC.4dm
- CMA_ItemCreate.4dm
- CMA_PaymentOrderInvoice.4dm
- CMAComInvoiceOneLine.4dm
- CMAComOrderOneLine.4dm
- CMAComplexImport.4dm
- CMAComplexPreflight.4dm
- CMAComplexProcess.4dm
- CMAIE_OrdImportOrders.4dm
- CMAIE_OrdImportOrdLines.4dm
- CMANewCommOrderLine.4dm

### custom (5 methods)  -- celery

- 00_TryCatch.4dm
- Exe_Cmdr_FutureStatement.4dm
- Exe_Cmdr_InvcLine.4dm
- Exe_Cmdr_OrdLine.4dm
- RelatedByNumberPrs.4dm

### HO (4 methods)

- HO_CatalogCCS.4dm
- HO_CatalogCCS_Report.4dm
- HO_CatalogCCS_dead.4dm
- HO_CatalogDuravent.4dm

### j (15 methods)   -- review

- jshowCurSelect.4dm
- jShowCurSelectProcess.4dm
- jshowDefaults.4dm
- jshowLetters.4dm
- jshowPopUps.4dm
- jshowProcesses.4dm
- jshowScripts.4dm
- JShowRelatedAll.4dm
- jSetFromArray.4dm
- jSetMenuNums.4dm
- jsetPages.4dm
- jrelateClrFiles.4dm
- jrelateLocalFil.4dm
- jReloadRecord.4dm
- jRestrictedFile.4dm

### Utility (1 method)

- UTFileNameLength.4dm

### Word (8 methods)  -- manage by keywords

- Key_CreateRecord.4dm
- Key_FindBuildMissing.4dm
- Key_Search.4dm
- KeyPageReadDataTest.4dm
- KeyReplaceComponent.4dm
- KwBubbles2Items.4dm
- KwItems2Bubbles.4dm
- UtBubbleListsLoad.4dm

### Loose Files -- create similar reporting features

- FormEventOnHeader.4dm
- SRE_Print.4dm
- URpt_SetUpPreview.4dm
- UserReport_iloProcedure.4dm

### Qx (158 methods) -- outdated

[Too many to list individually here; see source directory for full list]

### HTTP (127 methods) -- outdated

[Too many to list individually here; see source directory for full list]

### zzz (37 methods) -- outdated

[Too many to list individually here; see source directory for full list]

## Transfer/Rewrite Plan

To transfer or rewrite each utility one at a time, adapting for Django schema changes:

1. **Select a category and method**: Start with smaller categories like WC (4 methods) or HO (4 methods) for initial testing.
2. **Read the 4D code**: Examine the .4dm file to understand its functionality.
3. **Identify schema dependencies**: Note any database tables, fields, or relationships used in the 4D code.
4. **Map to Django models**: Translate 4D table/field references to corresponding Django models in WebClerk3.
5. **Rewrite in Python/Django**: Implement the logic using Django ORM, views, services, etc.
6. **Test and integrate**: Ensure the new implementation works with the current WebClerk3 codebase.
7. **Document changes**: Update this readme with status for each transferred utility.
8. **Repeat**: Move to the next utility.

### Transfer Status

- [ ] EDI methods (20)
- [ ] WC methods (4)
- [ ] HTML methods (29)
- [ ] Print methods (17)
- [ ] B2B methods (12)
- [ ] BarCode methods (7)
- [ ] CMA methods (17)
- [ ] custom methods (5)
- [ ] HO methods (4)
- [ ] j methods (15)
- [ ] Utility methods (1)
- [ ] Word methods (8)
- [ ] Loose files (4)
- [ ] Qx methods (158)
- [ ] HTTP methods (127)
- [ ] zzz methods (37)

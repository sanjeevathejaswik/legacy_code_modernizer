import java.util.*;
import java.text.SimpleDateFormat;
import java.io.BufferedWriter;
import java.io.FileWriter;
import java.io.IOException;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.text.NumberFormat;
import java.util.Locale;
import java.nio.charset.StandardCharsets; // For simple byte conversion
import java.security.SecureRandom; // For mock keys/signatures


public class DemoApplication {

    public static void main(String[] args) {
        try {
            User authenticatedUser = null;
            Scanner scanner = new Scanner(System.in);

            System.out.println("Starting Cheque Processing System with Enhanced Fraud Detection...");
            
            // Initialize services
            CurrencyExchangeService currencyExchangeService = new CurrencyExchangeService();
            SignatureVerificationService signatureVerificationService = new SignatureVerificationService();
            CoreBankingSystemUpdater coreBankingSystemUpdater = new CoreBankingSystemUpdater();
            UserService userService = new UserService(); // Initialize UserService
            ChequeHistoryManager chequeHistoryManager = new ChequeHistoryManager();
            FraudDetectionService fraudDetectionService = new FraudDetectionService();
            ExceptionReportManager exceptionReportManager = new ExceptionReportManager();
            ChequeStatusManager chequeStatusManager = new ChequeStatusManager();
            EmailNotificationService emailNotificationService = new EmailNotificationService();

            // Set up dependencies
            fraudDetectionService.setHistoryManager(chequeHistoryManager);

            // Initialize new services for image processing
            ChequeImageHandler imageHandler = new ChequeImageHandler();
            CryptographyService cryptoService = new CryptographyService();
            ClearinghouseService clearinghouseService = new ClearinghouseService();
            System.out.println("System initialized successfully.");

            // --- Login Process ---
            authenticatedUser = performLogin(scanner, userService);
            if (authenticatedUser == null) {
                System.out.println("Maximum login attempts reached. Exiting.");
                return; // Exit if login fails after retries
            }

            // Initialize cheque processor
            ChequeProcessor chequeProcessor = new ChequeProcessor(currencyExchangeService, signatureVerificationService,
                    coreBankingSystemUpdater, chequeHistoryManager, fraudDetectionService, exceptionReportManager, chequeStatusManager, emailNotificationService);
            
            System.out.println("System initialized successfully.");
    
            while (authenticatedUser != null) { // Continue loop only if authenticated
                System.out.println("\n--- Cheque Processing System ---");  
                System.out.println("1. Process a Single Cheque");  
                System.out.println("2. Process Multiple Cheques (Batch)");
                System.out.println("3. View Cheque History");  
                System.out.println("4. Currency Exchange Information");  
                System.out.println("5. Generate Cheque Reports");
                System.out.println("6. Scan, Encrypt, and Send Cheque Image"); // New Option
                System.out.println("7. Simulate Cheque Printing");
                System.out.println("8. Exit");  
                System.out.println("9. View Cheque Exception Report"); // New menu option
                System.out.println("10. View All Cheque Statuses"); // New menu option
                System.out.println("11. Cancel a Cheque"); // New menu option
                System.out.println("12. Record FIR/Legal Complaint for Bounced Cheque"); // New menu option
                System.out.println("13. Admin: Edit IFSC/Bank Codes");
                System.out.println("14. Admin: Manage Batches");
                System.out.println("15. Admin: Reset Stuck Transactions");
                System.out.print("Enter your choice: ");  
                int choice = scanner.nextInt();  
                scanner.nextLine(); // Consume newline  
    
                switch (choice) {  
                    case 1:  
                        System.out.println("Enter account number:");  
                        String accountNumber = scanner.nextLine();  
    
                        System.out.println("Enter cheque number:");  
                        String chequeNumber = scanner.nextLine();  
    
                        System.out.println("Enter currency (e.g., USD, EUR, GBP):");  
                        String currency = scanner.nextLine();  
    
                        System.out.println("Enter amount:");  
                        double amount = scanner.nextDouble();  
                        scanner.nextLine(); // Consume newline  
    
                        System.out.println("Enter signature:");  
                        String signature = scanner.nextLine();  
    
                        // Process the cheque  
                        chequeProcessor.processCheque(accountNumber, chequeNumber, currency, amount, signature);  
                        break;  
    
                    case 2:
                        // Process multiple cheques in a batch
                        processChequeBatch(scanner, chequeProcessor);
                        break;
    
                    case 3:  
                        System.out.println("Enter account number to view cheque history:");  
                        String historyAccountNumber = scanner.nextLine();  
                        chequeHistoryManager.displayChequeHistory(historyAccountNumber);  
                        break;  
    
                    case 4:
                        displayCurrencyExchangeMenu(scanner, currencyExchangeService);
                        break;
                        
                    case 5:
                        handleReportGeneration(scanner, chequeHistoryManager);
                        break;
    
                    case 6:
                        handleChequeImageSubmission(scanner, imageHandler, cryptoService, clearinghouseService, authenticatedUser);
                        break;
    
                    case 7:
                        // Assumes ChequePrintingService is an inner static class or accessible here
                        ChequePrintingService chequePrintingService = new ChequePrintingService();
                        handleChequePrinting(scanner, chequePrintingService);
                        break;
    
                    case 8:  
                        System.out.println("Logging out and exiting...");  
                        scanner.close();  
                        return;  
    
                    case 9:
                        exceptionReportManager.displayExceptions();
                        break;
    
                    case 10:
                        chequeStatusManager.displayAllStatuses();
                        break;
    
                    case 11:
                        System.out.print("Enter account number: ");
                        String cancelAccount = scanner.nextLine();
                        System.out.print("Enter cheque number: ");
                        String cancelCheque = scanner.nextLine();
                        chequeProcessor.cancelCheque(cancelAccount, cancelCheque);
                        break;

                    case 12:
                        System.out.print("Enter account number: ");
                        String firAccount = scanner.nextLine();
                        System.out.print("Enter cheque number: ");
                        String firCheque = scanner.nextLine();
                        System.out.print("Enter FIR/Complaint Number: ");
                        String firNumber = scanner.nextLine();
                        System.out.print("Enter Police Station: ");
                        String policeStation = scanner.nextLine();
                        System.out.print("Enter FIR/Complaint Date (YYYY-MM-DD): ");
                        String firDateStr = scanner.nextLine();
                        Date firDate;
                        try {
                            firDate = new SimpleDateFormat("yyyy-MM-dd").parse(firDateStr);
                        } catch (Exception e) {
                            System.out.println("Invalid date format. Please use YYYY-MM-DD.");
                            break;
                        }
                        System.out.print("Enter Remarks: ");
                        String firRemarks = scanner.nextLine();
                        exceptionReportManager.recordFIRDetails(firAccount, firCheque, firNumber, policeStation, firDate, firRemarks);
                        break;

                    case 13:
                        System.out.println("\n--- Admin: Edit IFSC/Bank Codes ---");
                        System.out.println("1. Add/Update IFSC");
                        System.out.println("2. Add/Update Bank Code");
                        System.out.println("3. View IFSCs");
                        System.out.println("4. View Bank Codes");
                        System.out.println("5. Return");
                        System.out.print("Enter your choice: ");
                        int adminChoice = scanner.nextInt();
                        scanner.nextLine();
                        switch (adminChoice) {
                            case 1:
                                System.out.print("Enter IFSC: ");
                                String ifsc = scanner.nextLine();
                                System.out.print("Enter Bank Code: ");
                                String bankCode = scanner.nextLine();
                                adminService.addOrUpdateIFSC(ifsc, bankCode);
                                break;
                            case 2:
                                System.out.print("Enter Bank Code: ");
                                String code = scanner.nextLine();
                                System.out.print("Enter Bank Name: ");
                                String name = scanner.nextLine();
                                adminService.addOrUpdateBankCode(code, name);
                                break;
                            case 3:
                                adminService.displayIFSCs();
                                break;
                            case 4:
                                adminService.displayBankCodes();
                                break;
                            default:
                                break;
                        }
                        break;

                    case 14:
                        System.out.println("\n--- Admin: Manage Batches ---");
                        System.out.println("1. Create Batch");
                        System.out.println("2. View Batches");
                        System.out.println("3. View Batch Details");
                        System.out.println("4. Return");
                        System.out.print("Enter your choice: ");
                        int batchChoice = scanner.nextInt();
                        scanner.nextLine();
                        switch (batchChoice) {
                            case 1:
                                System.out.print("Enter Batch ID: ");
                                String batchId = scanner.nextLine();
                                System.out.print("Enter number of cheques in batch: ");
                                int numCheques = scanner.nextInt();
                                scanner.nextLine();
                                List<BatchCheque> batchCheques = new ArrayList<>();
                                for (int i = 0; i < numCheques; i++) {
                                    System.out.println("Enter details for Cheque #" + (i + 1) + ":");
                                    System.out.print("Account number: ");
                                    String acc = scanner.nextLine();
                                    System.out.print("Cheque number: ");
                                    String chq = scanner.nextLine();
                                    System.out.print("Currency: ");
                                    String curr = scanner.nextLine();
                                    System.out.print("Amount: ");
                                    double amt = scanner.nextDouble();
                                    scanner.nextLine();
                                    System.out.print("Signature: ");
                                    String sig = scanner.nextLine();
                                    batchCheques.add(new BatchCheque(acc, chq, curr, amt, sig));
                                }
                                adminService.createBatch(batchId, batchCheques);
                                break;
                            case 2:
                                adminService.displayBatches();
                                break;
                            case 3:
                                System.out.print("Enter Batch ID: ");
                                String viewBatchId = scanner.nextLine();
                                adminService.displayBatchDetails(viewBatchId);
                                break;
                            default:
                                break;
                        }
                        break;

                    case 15:
                        System.out.println("\n--- Admin: Reset Stuck Transactions ---");
                        System.out.println("1. Mark Cheque as Stuck");
                        System.out.println("2. Reset Stuck Cheque");
                        System.out.println("3. View Stuck Transactions");
                        System.out.println("4. Return");
                        System.out.print("Enter your choice: ");
                        int stuckChoice = scanner.nextInt();
                        scanner.nextLine();
                        switch (stuckChoice) {
                            case 1:
                                System.out.print("Enter Cheque Number to mark as stuck: ");
                                String stuckChq = scanner.nextLine();
                                adminService.markTransactionStuck(stuckChq);
                                break;
                            case 2:
                                System.out.print("Enter Cheque Number to reset: ");
                                String resetChq = scanner.nextLine();
                                adminService.resetStuckTransaction(resetChq);
                                break;
                            case 3:
                                adminService.displayStuckTransactions();
                                break;
                            default:
                                break;
                        }
                        break;
    
                    default:  
                        System.out.println("Invalid choice. Please try again.");  
                }
            }
        } catch (Exception ex) {
            Logger.error("Fatal error in main: " + ex.getMessage());
            ex.printStackTrace();
        }
    }

    /**
     * Handles the user login process.
     * @param scanner The scanner for user input
     * @param userService The user service for authentication
     * @return The authenticated User object, or null if login fails after retries
     */
    private static User performLogin(Scanner scanner, UserService userService) {
        final int MAX_ATTEMPTS = 3;
        for (int attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
            try {
                System.out.println("\n--- Login ---");
                System.out.print("Enter username: ");
                String username = scanner.nextLine();
                System.out.print("Enter password: ");
                String password = scanner.nextLine(); // In a real app, use a secure way to read password

                User user = userService.authenticate(username, password);
                if (user != null) {
                    Logger.info("User logged in: " + username);
                    System.out.println("Welcome, " + user.getUsername() + " (" + user.getRole() + ")!");
                    return user; // Login successful
                } else {
                    Logger.warn("Failed login attempt for user: " + username);
                    System.out.println("Invalid username or password. Attempt " + attempt + " of " + MAX_ATTEMPTS);
                }
            } catch (Exception ex) {
                Logger.error("Error during login: " + ex.getMessage());
            }
        }
        return null; // Login failed after max attempts
    }

    /**
     * Handles processing multiple cheques in a batch.
     * Prompts the user for the number of cheques and their details.
     * @param scanner The scanner for user input
     * @param chequeProcessor The cheque processor service
     */
    private static void processChequeBatch(Scanner scanner, ChequeProcessor chequeProcessor) {
        try {
            System.out.println("\n--- Batch Cheque Processing ---");
            System.out.print("Enter the number of cheques in the batch: ");
            int batchSize = scanner.nextInt();
            scanner.nextLine(); // Consume newline

            List<BatchCheque> chequesToProcess = new ArrayList<>();

            for (int i = 0; i < batchSize; i++) {
                try {
                    System.out.println("\nEnter details for Cheque #" + (i + 1) + ":");
                    System.out.print("Account number: ");
                    String accountNumber = scanner.nextLine();
                    System.out.print("Cheque number: ");
                    String chequeNumber = scanner.nextLine();
                    System.out.print("Currency (e.g., USD, EUR, GBP): ");
                    String currency = scanner.nextLine();
                    System.out.print("Amount: ");
                    double amount = scanner.nextDouble();
                    scanner.nextLine(); // Consume newline
                    System.out.print("Signature: ");
                    String signature = scanner.nextLine();

                    chequesToProcess.add(new BatchCheque(accountNumber, chequeNumber, currency, amount, signature));
                } catch (Exception ex) {
                    Logger.error("Error collecting cheque batch input: " + ex.getMessage());
                    scanner.nextLine(); // Clear buffer
                }
            }

            System.out.println("\nProcessing batch...");
            chequesToProcess.forEach(cheque -> {
                try {
                    chequeProcessor.processCheque(cheque.accountNumber, cheque.chequeNumber, cheque.currency, cheque.amount, cheque.signature);
                } catch (Exception ex) {
                    Logger.error("Error processing cheque in batch: " + ex.getMessage());
                }
            });
        } catch (Exception ex) {
            Logger.error("Batch processing error: " + ex.getMessage());
        }
    }
    
    /**
     * Display the currency exchange menu and handle user interactions
     * @param scanner The scanner for user input
     * @param currencyExchangeService The currency exchange service
     */
    private static void displayCurrencyExchangeMenu(Scanner scanner, CurrencyExchangeService currencyExchangeService) {
        while (true) {
            System.out.println("\n--- Currency Exchange Menu ---");
            System.out.println("1. View Supported Currencies");
            System.out.println("2. Get Exchange Rate");
            System.out.println("3. Get Detailed Exchange Rate Information");
            System.out.println("4. Convert Currency");
            System.out.println("5. Return to Main Menu");
            System.out.print("Enter your choice: ");
            
            int choice = scanner.nextInt();
            scanner.nextLine(); // Consume newline
            
            switch (choice) {
                case 1:
                    // Display supported currencies
                    List<String> supportedCurrencies = currencyExchangeService.getSupportedCurrencies();
                    System.out.println("\nSupported Currencies:");
                    for (String currencyCode : supportedCurrencies) {
                        System.out.println("- " + currencyCode);
                    }
                    break;
                    
                case 2:
                    // Get exchange rate
                    System.out.print("Enter currency code: ");
                    String currencyCode = scanner.nextLine().toUpperCase();
                    double rate = currencyExchangeService.getExchangeRate(currencyCode);
                    
                    if (rate > 0) {
                        System.out.println("Exchange rate for " + currencyCode + ": " + rate);
                    } else {
                        System.out.println("Currency not supported or exchange rate unavailable.");
                    }
                    break;
                    
                case 3:
                    // Get detailed exchange rate information
                    System.out.print("Enter currency code: ");
                    String detailCurrencyCode = scanner.nextLine().toUpperCase();
                    Map<String, Double> detailedRates = currencyExchangeService.getDetailedExchangeRates(detailCurrencyCode);
                    
                    if (!detailedRates.isEmpty()) {
                        System.out.println("\nDetailed Exchange Rate Information for " + detailCurrencyCode + ":");
                        System.out.println("Mid Rate: " + detailedRates.get("mid"));
                        System.out.println("Buy Rate: " + detailedRates.get("buy"));
                        System.out.println("Sell Rate: " + detailedRates.get("sell"));
                        System.out.println("Fee Rate: " + detailedRates.get("fee"));
                    } else {
                        System.out.println("Currency not supported or exchange rate unavailable.");
                    }
                    break;
                    
                case 4:
                    // Convert currency
                    System.out.print("Enter amount: ");
                    double amount = scanner.nextDouble();
                    scanner.nextLine(); // Consume newline
                    
                    System.out.print("Enter source currency code: ");
                    String fromCurrency = scanner.nextLine().toUpperCase();
                    
                    System.out.print("Enter target currency code: ");
                    String toCurrency = scanner.nextLine().toUpperCase();
                    
                    double convertedAmount = currencyExchangeService.convertCurrency(amount, fromCurrency, toCurrency);
                    
                    if (convertedAmount > 0) {
                        System.out.printf("%.2f %s = %.2f %s\n", amount, fromCurrency, convertedAmount, toCurrency);
                    } else {
                        System.out.println("Currency conversion failed. Please check the currency codes.");
                    }
                    break;
                    
                case 5:
                    // Return to main menu
                    return;
                    
                default:
                    System.out.println("Invalid choice. Please try again.");
            }
        }
    }

    /**
     * Handles the report generation menu and logic.
     * @param scanner The scanner for user input
     * @param chequeHistoryManager The cheque history manager
     */
    private static void handleReportGeneration(Scanner scanner, ChequeHistoryManager chequeHistoryManager) {
        System.out.println("\n--- Generate Cheque Reports ---");
        System.out.println("1. Daily Report (Today)");
        System.out.println("2. Weekly Report (Last 7 Days)");
        System.out.println("3. Monthly Report (Last 30 Days)");
        System.out.println("4. Custom Date Range Report");
        System.out.println("5. Return to Main Menu");
        System.out.print("Enter your choice: ");
        int choice = scanner.nextInt();
        scanner.nextLine(); // Consume newline

        LocalDate endDate = LocalDate.now();
        LocalDate startDate;
        String reportNamePrefix;

        switch (choice) {
            case 1: // Daily
                startDate = endDate;
                reportNamePrefix = "daily_report_";
                break;
            case 2: // Weekly
                startDate = endDate.minusDays(6); // Last 7 days including today
                reportNamePrefix = "weekly_report_";
                break;
            case 3: // Monthly
                startDate = endDate.minusDays(29); // Last 30 days including today
                reportNamePrefix = "monthly_report_";
                break;
            case 4: // Custom
                System.out.print("Enter start date (YYYY-MM-DD): ");
                String startDateStr = scanner.nextLine();
                System.out.print("Enter end date (YYYY-MM-DD): ");
                String endDateStr = scanner.nextLine();
                try {
                    startDate = LocalDate.parse(startDateStr, DateTimeFormatter.ISO_LOCAL_DATE);
                    endDate = LocalDate.parse(endDateStr, DateTimeFormatter.ISO_LOCAL_DATE);
                } catch (Exception e) {
                    System.out.println("Invalid date format. Please use YYYY-MM-DD.");
                    return;
                }
                if (startDate.isAfter(endDate)) {
                    System.out.println("Start date cannot be after end date.");
                    return;
                }
                reportNamePrefix = "custom_report_";
                break;
            case 5:
                return; // Return to main menu
            default:
                System.out.println("Invalid choice. Please try again.");
                return;
        }

        List<ChequeHistoryManager.ChequeRecord> records = chequeHistoryManager.getAllChequeRecordsInPeriod(startDate, endDate);

        if (records.isEmpty()) {
            System.out.println("No cheque records found for the selected period.");
            return;
        }

        String csvData = chequeHistoryManager.generateChequeReportCSV(records);
        String fileName = reportNamePrefix + startDate.format(DateTimeFormatter.ISO_LOCAL_DATE) +
                          "_to_" + endDate.format(DateTimeFormatter.ISO_LOCAL_DATE) + ".csv";

        try (BufferedWriter writer = new BufferedWriter(new FileWriter(fileName))) {
            writer.write(csvData);
            System.out.println("Report generated successfully: " + fileName);
        } catch (IOException e) {
            System.err.println("Error writing report to file: " + e.getMessage());
        }
    }

    /**
     * Handles the cheque printing simulation.
     * @param scanner The scanner for user input
     * @param printingService The cheque printing service
     */
    private static void handleChequePrinting(Scanner scanner, ChequePrintingService printingService) {
        System.out.println("\n--- Simulate Cheque Printing ---");

        System.out.print("Enter Payee Name: ");
        String payeeName = scanner.nextLine();

        System.out.print("Enter Amount: ");
        double amount = scanner.nextDouble();
        scanner.nextLine(); // Consume newline

        System.out.print("Enter Date (YYYY-MM-DD): ");
        String dateStr = scanner.nextLine();
        Date chequeDate;
        try {
            chequeDate = new SimpleDateFormat("yyyy-MM-dd").parse(dateStr);
        } catch (java.text.ParseException e) {
            System.out.println("Invalid date format. Please use YYYY-MM-DD. Using current date.");
            chequeDate = new Date();
        }

        System.out.print("Enter Account Number: ");
        String accountNumber = scanner.nextLine();

        System.out.print("Enter Cheque Number: ");
        String chequeNumber = scanner.nextLine();

        // You can make bankName configurable or a constant
        String bankName = "Global Trust Bank";

        printingService.printCheque(payeeName, amount, chequeDate, accountNumber, chequeNumber, bankName);
    }

    /**
     * Handles the process of "scanning", encrypting, signing, and "sending" a cheque image.
     * @param scanner Input scanner
     * @param imageHandler Service to handle image "upload"
     * @param cryptoService Service for encryption and signing
     * @param clearinghouseService Service to "send" to clearinghouse
     * @param currentUser The currently logged-in user
     */
    private static void handleChequeImageSubmission(Scanner scanner,
                                                    ChequeImageHandler imageHandler,
                                                    CryptographyService cryptoService,
                                                    ClearinghouseService clearinghouseService,
                                                    User currentUser) {
        System.out.println("\n--- Cheque Image Submission ---");
        System.out.print("Enter Account Number for the cheque: ");
        String accountNumber = scanner.nextLine();
        System.out.print("Enter Cheque Number: ");
        String chequeNumber = scanner.nextLine();
        System.out.print("Enter path to cheque image file (e.g., /path/to/cheque.jpg): ");
        String imagePath = scanner.nextLine();

        // 1. Simulate scanning and uploading image
        byte[] imageData = imageHandler.loadImageData(imagePath);
        if (imageData == null) {
            System.out.println("Failed to load image data. Aborting submission.");
            return;
        }
        System.out.println("Cheque image \"uploaded\" successfully from: " + imagePath);

        // 2. Encrypt the image data
        // In a real system, key management would be crucial.
        String encryptionKey = "a-very-secure-encryption-key"; // Placeholder
        byte[] encryptedImageData = cryptoService.encryptData(imageData, encryptionKey);
        System.out.println("Image data encrypted.");

        // 3. Sign the encrypted image data
        String privateKey = currentUser.getUsername() + "-private-key"; // Placeholder
        String digitalSignature = cryptoService.signData(encryptedImageData, privateKey);
        System.out.println("Encrypted image data signed. Signature: " + digitalSignature.substring(0, 10) + "..."); // Show partial signature

        // 4. Send to clearinghouse
        clearinghouseService.submitToClearinghouse(accountNumber, chequeNumber, encryptedImageData, digitalSignature);
    }

    // --- Existing Inner Classes (User, UserService, BatchCheque) ---
    // ... (Keep existing inner classes as they are)
    static class EmailNotificationService {
    public void sendEmail(String to, String subject, String body) {
        // In a real system, integrate with JavaMail or an SMTP server.
        // For simulation, just print to console.
        System.out.println("\n--- EMAIL NOTIFICATION ---");
        System.out.println("To: " + to);
        System.out.println("Subject: " + subject);
        System.out.println("Body:\n" + body);
        System.out.println("--------------------------\n");
    }
        }
        
    /**
     * Service for simulating cheque printing.
     */
    static class ChequePrintingService {
        public void printCheque(String payeeName, double amount, Date date, String accountNumber, String chequeNumber, String bankName) {
            SimpleDateFormat dateFormat = new SimpleDateFormat("dd-MMM-yyyy");
            NumberFormat currencyFormatter = NumberFormat.getCurrencyInstance(Locale.US); // Assuming USD

            System.out.println("\n+----------------------------------------------------------------------+");
            System.out.printf("| %-50s Date: %-10s |\n", bankName.toUpperCase(), dateFormat.format(date));
            System.out.println("|                                                                      |");
            System.out.printf("| Pay To: %-30s Amount: %-15s |\n", payeeName, currencyFormatter.format(amount));
            // Amount in words is complex, for simulation, we can skip or put a placeholder
            System.out.printf("| Amount in Words: %-45s |\n", "*(Numeric Amount Above)*");
            System.out.println("|                                                                      |");
            System.out.println("|                                                                      |");
            System.out.printf("| Account No: %-25s Cheque No: %-15s |\n", accountNumber, chequeNumber);
            System.out.println("|                                                                      |");
            System.out.println("|                                                 Signature:           |");
            System.out.println("|                                                 -------------------- |");
            System.out.println("+----------------------------------------------------------------------+");
            System.out.println("Cheque simulation printed successfully.\n");
        }
    }
    /**
 * Represents a user of the system (employee or account holder).
 */
    static class User {
        private String username;
        private String password; // In a real app, this would be hashed
        private String role; // e.g., "EMPLOYEE", "ACCOUNT_HOLDER"

        public User(String username, String password, String role) {
            this.username = username;
            this.password = password;
            this.role = role;
        }

        public String getUsername() {
            return username;
        }

        public String getPassword() {
            return password;
        }

        public String getRole() {
            return role;
        }
    }

    /**
     * Service for managing users and handling authentication.
     */
    static class UserService {
        private Map<String, User> users = new HashMap<>();

        public UserService() {
            // Add some sample users for demonstration
            registerUser("employee1", "password123", "EMPLOYEE");
            registerUser("account1001", "chequeuser", "ACCOUNT_HOLDER");
            registerUser("account1002", "securepass", "ACCOUNT_HOLDER");
        }

        /**
         * Registers a new user.
         * @param username The username
         * @param password The password
         * @param role The user's role
         */
        public void registerUser(String username, String password, String role) {
            users.put(username, new User(username, password, role));
            System.out.println("User registered: " + username + " (" + role + ")");
        }

        /**
         * Authenticates a user based on username and password.
         * @param username The username
         * @param password The password
         * @return The authenticated User object if successful, null otherwise
         */
        public User authenticate(String username, String password) {
            User user = users.get(username);
            if (user != null && user.getPassword().equals(password)) {
                System.out.println("Authentication successful for user: " + username);
                return user;
            }
            System.out.println("Authentication failed for user: " + username);
            return null;
        }
    }

    /**
     * Represents a single cheque transaction for batch processing.
     */
    class BatchCheque {
        String accountNumber;
        String chequeNumber;
        String currency;
        double amount;
        String signature;

        public BatchCheque(String accountNumber, String chequeNumber, String currency, double amount, String signature) {
            this.accountNumber = accountNumber;
            this.chequeNumber = chequeNumber;
            this.currency = currency;
            this.amount = amount;
            this.signature = signature;
        }
    }

    /**
     * Manages exception reports for cheques (bounced, duplicate, altered, delayed).
     * Now supports recording FIR/legal complaint details for bounced cheques.
     */
    static class ExceptionReportManager {
        static class ExceptionRecord {
            String accountNumber, chequeNumber, type, details;
            Date date;
            FIRDetails firDetails; // New: FIR/legal complaint details

            ExceptionRecord(String accountNumber, String chequeNumber, String type, String details, Date date) {
                this.accountNumber = accountNumber;
                this.chequeNumber = chequeNumber;
                this.type = type;
                this.details = details;
                this.date = date;
                this.firDetails = null;
            }
        }

    // New: FIR/legal complaint details class
        static class FIRDetails {
            String firNumber;
            String policeStation;
            Date firDate;
            String remarks;

            FIRDetails(String firNumber, String policeStation, Date firDate, String remarks) {
                this.firNumber = firNumber;
                this.policeStation = policeStation;
                this.firDate = firDate;
                this.remarks = remarks;
            }
        }

        private List<ExceptionRecord> exceptions = new ArrayList<>();

        public void reportException(String accountNumber, String chequeNumber, String type, String details) {
            exceptions.add(new ExceptionRecord(accountNumber, chequeNumber, type, details, new Date()));
            System.out.println("Exception reported: " + type + " for Cheque " + chequeNumber + " (" + details + ")");
        }

        // New: Record FIR/legal complaint details for a bounced cheque
        public boolean recordFIRDetails(String accountNumber, String chequeNumber, String firNumber, String policeStation, Date firDate, String remarks) {
            for (ExceptionRecord ex : exceptions) {
                if (ex.accountNumber.equals(accountNumber)
                        && ex.chequeNumber.equals(chequeNumber)
                        && "Bounced".equalsIgnoreCase(ex.type)) {
                    ex.firDetails = new FIRDetails(firNumber, policeStation, firDate, remarks);
                    System.out.println("FIR/legal complaint details recorded for bounced cheque " + chequeNumber);
                    return true;
                }
            }
            System.out.println("No bounced cheque exception found for the given account and cheque number.");
            return false;
        }

        public void displayExceptions() {
            if (exceptions.isEmpty()) {
                System.out.println("No cheque exceptions reported.");
                return;
            }
            System.out.println("\n--- Cheque Exception Report ---");
            for (ExceptionRecord ex : exceptions) {
                System.out.printf("Date: %s | Account: %s | Cheque: %s | Type: %s | Details: %s\n",
                    new SimpleDateFormat("yyyy-MM-dd HH:mm").format(ex.date),
                    ex.accountNumber, ex.chequeNumber, ex.type, ex.details);
                // Show FIR/legal complaint details if present
                if ("Bounced".equalsIgnoreCase(ex.type) && ex.firDetails != null) {
                    System.out.printf("   FIR No: %s | Police Station: %s | FIR Date: %s | Remarks: %s\n",
                        ex.firDetails.firNumber,
                        ex.firDetails.policeStation,
                        new SimpleDateFormat("yyyy-MM-dd").format(ex.firDetails.firDate),
                        ex.firDetails.remarks);
                }
            }
        }
    }

    /**
     * Enum to represent cheque status.
     */
    enum ChequeStatus {
        ISSUED,
        PROCESSED,
        CANCELED
    }

    /**
     * ChequeStatusManager to track the status of cheques.
     */
    static class ChequeStatusManager {
        // Key: accountNumber + ":" + chequeNumber, Value: ChequeStatus
        private Map<String, ChequeStatus> chequeStatusMap = new HashMap<>();

        public void setStatus(String accountNumber, String chequeNumber, ChequeStatus status) {
            chequeStatusMap.put(accountNumber + ":" + chequeNumber, status);
            System.out.println("Status of cheque " + chequeNumber + " for account " + accountNumber + " set to " + status);
        }

        public ChequeStatus getStatus(String accountNumber, String chequeNumber) {
            return chequeStatusMap.getOrDefault(accountNumber + ":" + chequeNumber, null);
        }

        public void displayAllStatuses() {
            if (chequeStatusMap.isEmpty()) {
                System.out.println("No cheque statuses recorded.");
                return;
            }
            System.out.println("\n--- Cheque Statuses ---");
            for (Map.Entry<String, ChequeStatus> entry : chequeStatusMap.entrySet()) {
                String[] parts = entry.getKey().split(":");
                System.out.printf("Account: %s | Cheque: %s | Status: %s\n", parts[0], parts[1], entry.getValue());
            }
        }
    }

    /**
     * Simple Logger utility for error/info/debug logging.
     */
    static class Logger {
        public enum Level { INFO, WARN, ERROR, DEBUG }

        public static void log(Level level, String message) {
            String timestamp = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss").format(new Date());
            System.out.printf("[%s] [%s] %s%n", timestamp, level, message);
        }

        public static void info(String message) { log(Level.INFO, message); }
        public static void warn(String message) { log(Level.WARN, message); }
        public static void error(String message) { log(Level.ERROR, message); }
        public static void debug(String message) { log(Level.DEBUG, message); }
        }

    /**
     * Simulates handling of cheque images.
     */
    static class ChequeImageHandler {
        /**
         * Simulates loading image data from a file path.
         * In a real application, this would involve actual file I/O and image processing.
         * @param filePath The path to the image file.
         * @return A byte array representing the image data, or null on failure.
         */
        public byte[] loadImageData(String filePath) {
            if (filePath == null || filePath.trim().isEmpty()) {
                System.out.println("Error: Image file path cannot be empty.");
                return null;
            }
            // Simulate reading file content. For this demo, we'll just use the path string as bytes.
            // In a real app: Files.readAllBytes(Paths.get(filePath));
            System.out.println("Simulating reading image from: " + filePath);
            return ("ImageData:" + filePath + ":Content").getBytes(StandardCharsets.UTF_8);
        }
    }

    /**
     * Simulates cryptographic operations like encryption and digital signing.
     */
    static class CryptographyService {
        /**
         * Simulates encrypting data.
         * @param data The data to encrypt.
         * @param key The encryption key.
         * @return Mock encrypted data.
         */
        public byte[] encryptData(byte[] data, String key) {
            // This is a placeholder. Real encryption would use JCA (Java Cryptography Architecture).
            // For simulation, let's just prepend "encrypted-" and append the key.
            String originalData = new String(data, StandardCharsets.UTF_8);
            String encryptedString = "encrypted(" + key + "):" + originalData;
            return encryptedString.getBytes(StandardCharsets.UTF_8);
        }

        /**
         * Simulates digitally signing data.
         * @param data The data to sign.
         * @param privateKey The private key for signing.
         * @return A mock digital signature.
         */
        public String signData(byte[] data, String privateKey) {
            // This is a placeholder. Real digital signatures use algorithms like RSA, ECDSA.
            // For simulation, create a simple hash-like string.
            int hashCode = Arrays.hashCode(data);
            return "signature(" + privateKey + "):" + Integer.toHexString(hashCode) + Long.toHexString(System.nanoTime());
        }
    }

    /**
     * Simulates sending data to a clearinghouse.
     */
    static class ClearinghouseService {
        /**
         * Simulates submitting cheque image data and signature to a clearinghouse.
         * @param accountNumber The account number.
         * @param chequeNumber The cheque number.
         * @param encryptedImageData The encrypted image data.
         * @param digitalSignature The digital signature.
         */
        public void submitToClearinghouse(String accountNumber, String chequeNumber, byte[] encryptedImageData, String digitalSignature) {
            System.out.println("\n--- Submitting to Clearinghouse ---");
            System.out.println("Account: " + accountNumber + ", Cheque: " + chequeNumber);
            System.out.println("Encrypted Data Length: " + encryptedImageData.length + " bytes");
            System.out.println("Digital Signature: " + digitalSignature.substring(0, Math.min(digitalSignature.length(), 20)) + "..."); // Show partial signature
            System.out.println("Simulating sending via SFTP/REST API...");
            System.out.println("Submission to clearinghouse successful (simulated).");
            System.out.println("---------------------------------");
        }
    }


    /**
     * Service for verifying signatures on cheques.
     * This is a simplified implementation for demonstration purposes.
     */
    static class SignatureVerificationService {
        private Map<String, String> accountSignatures = new HashMap<>();

        public SignatureVerificationService() {
            // Initialize with some sample signatures for testing
            accountSignatures.put("1001", "John Doe");
            accountSignatures.put("1002", "Jane Smith");
            accountSignatures.put("1003", "Robert Johnson");
        }

        /**
         * Verifies if the provided signature matches the one on file for the account.
         *
         * @param accountNumber The account number
         * @param signature The signature to verify
         * @return true if the signature is valid, false otherwise
         */
        public boolean verifySignature(String accountNumber, String signature) {
            System.out.println("Verifying signature for account: " + accountNumber);

            // If we don't have a signature on file, accept any signature (for demo purposes)
            if (!accountSignatures.containsKey(accountNumber)) {
                System.out.println("No signature on file for account: " + accountNumber + ". Accepting new signature.");
                accountSignatures.put(accountNumber, signature);
                return true;
            }

            // Compare the provided signature with the one on file
            String storedSignature = accountSignatures.get(accountNumber);
            boolean isValid = storedSignature.equals(signature);

            if (isValid) {
                System.out.println("Signature verified successfully.");
            } else {
                System.out.println("Signature verification failed.");
            }

            return isValid;
        }

        /**
         * Updates the signature on file for an account.
         *
         * @param accountNumber The account number
         * @param newSignature The new signature
         */
        public void updateSignature(String accountNumber, String newSignature) {
            accountSignatures.put(accountNumber, newSignature);
            System.out.println("Signature updated for account: " + accountNumber);
        }
    }

    /**
     * Module for processing cheques with signature verification, fraud detection,
     * currency conversion, and core banking system update.
     */
    static class ChequeProcessor {
        private CurrencyExchangeService currencyExchangeService;
        private SignatureVerificationService signatureVerificationService;
        private CoreBankingSystemUpdater coreBankingSystemUpdater;
        private ChequeHistoryManager chequeHistoryManager;
        private FraudDetectionService fraudDetectionService;
        private ExceptionReportManager exceptionReportManager;
        private ChequeStatusManager chequeStatusManager;
        private EmailNotificationService emailNotificationService;

        public ChequeProcessor(CurrencyExchangeService currencyExchangeService,
                               SignatureVerificationService signatureVerificationService,
                               CoreBankingSystemUpdater coreBankingSystemUpdater,
                               ChequeHistoryManager chequeHistoryManager,
                               FraudDetectionService fraudDetectionService,
                               ExceptionReportManager exceptionReportManager,
                               ChequeStatusManager chequeStatusManager,
                               EmailNotificationService emailNotificationService) {
            this.currencyExchangeService = currencyExchangeService;
            this.signatureVerificationService = signatureVerificationService;
            this.coreBankingSystemUpdater = coreBankingSystemUpdater;
            this.chequeHistoryManager = chequeHistoryManager;
            this.fraudDetectionService = fraudDetectionService;
            this.exceptionReportManager = exceptionReportManager;
            this.chequeStatusManager = chequeStatusManager;
            this.emailNotificationService = emailNotificationService;
        }

        public void processCheque(String accountNumber, String chequeNumber, String currency, double amount, String signature) {
            try {
                // Mark as issued if not already tracked
                if (chequeStatusManager.getStatus(accountNumber, chequeNumber) == null) {
                    chequeStatusManager.setStatus(accountNumber, chequeNumber, ChequeStatus.ISSUED);
                }

                Logger.info("Processing cheque: " + chequeNumber + " for account: " + accountNumber);

                System.out.println("Processing cheque...");

                // Step 1: Verify signature
                if (!signatureVerificationService.verifySignature(accountNumber, signature)) {
                    exceptionReportManager.reportException(accountNumber, chequeNumber, "Altered", "Signature mismatch");
                    Logger.warn("Signature verification failed for cheque: " + chequeNumber);
                    System.out.println("Signature verification failed. Cheque processing aborted.");
                    // Send email notification
                    emailNotificationService.sendEmail(
                        accountNumber + "@bank.com",
                        "Cheque Validation Failure",
                        "Cheque " + chequeNumber + " for account " + accountNumber + " failed signature verification."
                    );
                    return;
                }

                // Step 2: Fraud detection
                if (fraudDetectionService.isFraudulentCheque(accountNumber, chequeNumber, amount)) {
                    exceptionReportManager.reportException(accountNumber, chequeNumber, "Duplicate", "Fraudulent or duplicate cheque detected");
                    Logger.warn("Fraudulent cheque detected: " + chequeNumber);
                    System.out.println("Fraudulent cheque detected. Cheque processing aborted.");
                    // Send email notification
                    emailNotificationService.sendEmail(
                        accountNumber + "@bank.com",
                        "Fraud Detection Alert",
                        "Potential fraud detected for cheque " + chequeNumber + " on account " + accountNumber + "."
                    );
                    return;
                }

                // Simulate bounced cheque (for demo, if amount > 50000)
                if (amount > 50000) {
                    exceptionReportManager.reportException(accountNumber, chequeNumber, "Bounced", "Insufficient funds (simulated)");
                    Logger.warn("Cheque bounced due to high amount: " + chequeNumber);
                    System.out.println("Cheque bounced due to insufficient funds. Cheque processing aborted.");
                    // Send email notification
                    emailNotificationService.sendEmail(
                        accountNumber + "@bank.com",
                        "Cheque Bounced Notification",
                        "Cheque " + chequeNumber + " for account " + accountNumber + " has bounced due to insufficient funds."
                    );
                    return;
                }

                // Simulate delayed cheque (for demo, if cheque number ends with '9')
                if (chequeNumber.endsWith("9")) {
                    exceptionReportManager.reportException(accountNumber, chequeNumber, "Delayed", "Cheque processing delayed (simulated)");
                    Logger.info("Cheque processing delayed for cheque: " + chequeNumber);
                    System.out.println("Cheque processing delayed (simulated).");
                    // Optional: send notification for delayed cheques if desired
                }

                // Step 3: Get detailed exchange rate information if currency is not local
                double amountInLocalCurrency = amount;
                if (!"USD".equalsIgnoreCase(currency)) { // USD is the base currency
                    Map<String, Double> detailedRates = currencyExchangeService.getDetailedExchangeRates(currency);

                    if (detailedRates.isEmpty()) {
                        Logger.error("Exchange rate unavailable for currency: " + currency);
                        System.out.println("Failed to fetch exchange rate. Cheque processing aborted.");
                        return;
                    }

                    // Use the buy rate for incoming transactions
                    double buyRate = detailedRates.get("buy");
                    double fee = detailedRates.get("fee");

                    // Step 4: Convert amount to local currency with detailed calculations
                    amountInLocalCurrency = amount * buyRate;
                    double feeAmount = amount * fee;

                    System.out.println("Currency: " + currency.toUpperCase());
                    System.out.println("Original amount: " + amount);
                    System.out.println("Exchange rate (buy): " + buyRate);
                    System.out.println("Fee rate: " + fee);
                    System.out.println("Fee amount: " + feeAmount);
                    System.out.println("Amount in local currency (before fees): " + amountInLocalCurrency);

                    // Apply fee
                    amountInLocalCurrency -= feeAmount;
                    System.out.println("Final amount in local currency (USD): " + amountInLocalCurrency);
                } else {
                    System.out.println("Processing in local currency (USD): " + amountInLocalCurrency);
                }

                // Step 5: Update core banking system
                coreBankingSystemUpdater.updateCoreBankingSystem(accountNumber, amountInLocalCurrency);

                // Step 6: Record cheque history
                chequeHistoryManager.recordCheque(accountNumber, chequeNumber, currency, amount, new java.util.Date());

                // If cheque is processed successfully:
                chequeStatusManager.setStatus(accountNumber, chequeNumber, ChequeStatus.PROCESSED);
                Logger.info("Cheque processed successfully: " + chequeNumber);
                System.out.println("Cheque processed successfully.");
            } catch (Exception ex) {
                Logger.error("Error processing cheque " + chequeNumber + ": " + ex.getMessage());
                exceptionReportManager.reportException(accountNumber, chequeNumber, "ProcessingError", ex.getMessage());
                System.out.println("An error occurred during cheque processing. Please check logs.");
                // Send email notification for processing error
                emailNotificationService.sendEmail(
                    accountNumber + "@bank.com",
                    "Cheque Processing Error",
                    "An error occurred while processing cheque " + chequeNumber + " for account " + accountNumber + ": " + ex.getMessage()
                );
            }
        }

        // Add a method to cancel a cheque
        public void cancelCheque(String accountNumber, String chequeNumber) {
            try {
                chequeStatusManager.setStatus(accountNumber, chequeNumber, ChequeStatus.CANCELED);
                Logger.info("Cheque canceled: " + chequeNumber + " for account: " + accountNumber);
                System.out.println("Cheque " + chequeNumber + " for account " + accountNumber + " has been canceled.");
            } catch (Exception ex) {
                Logger.error("Error canceling cheque " + chequeNumber + ": " + ex.getMessage());
                System.out.println("An error occurred while canceling the cheque.");
            }
        }
    }

    /**
     * Enhanced Currency Exchange Service
     * Supports multiple currencies with detailed exchange rate calculations
     * and dynamic fetching of rates from external sources.
     */
    static class CurrencyExchangeService {
        private Map<String, CurrencyRate> exchangeRateCache = new HashMap<>();
        private static final String BASE_CURRENCY = "USD";
        private static final long CACHE_EXPIRY_MINUTES = 60; // Cache expiry time in minutes
        private static final String API_KEY = "demo"; // Replace with your actual API key for production

        // Fallback exchange rates in case API is unavailable
        private static final Map<String, Double> FALLBACK_RATES = new HashMap<String, Double>() {{
            put("EUR", 1.1);
            put("GBP", 1.3);
            put("INR", 0.013);
            put("JPY", 0.0091);
            put("CAD", 0.74);
            put("AUD", 0.67);
            put("CHF", 1.12);
            put("CNY", 0.14);
            put("HKD", 0.13);
            put("NZD", 0.62);
        }};

        /**
         * Get the exchange rate for a specific currency
         * @param currency The currency code (e.g., EUR, GBP)
         * @return The exchange rate relative to the base currency (USD)
         */
        public double getExchangeRate(String currency) {
            System.out.println("Fetching exchange rate for currency: " + currency);

            // Standardize currency code
            String currencyCode = currency.toUpperCase();

            // Return 1.0 if it's the base currency
            if (BASE_CURRENCY.equals(currencyCode)) {
                return 1.0;
            }

            // Check cache first
            if (isCacheValid(currencyCode)) {
                CurrencyRate cachedRate = exchangeRateCache.get(currencyCode);
                System.out.println("Using cached rate: " + cachedRate.getRate() + " (Last updated: " +
                        cachedRate.getLastUpdated().format(java.time.format.DateTimeFormatter.ISO_LOCAL_DATE_TIME) + ")");
                return cachedRate.getRate();
            }

            // Try to fetch from external API
            try {
                double apiRate = fetchRateFromAPI(currencyCode);
                if (apiRate > 0) {
                    // Cache the new rate
                    exchangeRateCache.put(currencyCode, new CurrencyRate(apiRate, java.time.LocalDateTime.now()));
                    return apiRate;
                }
            } catch (Exception e) {
                System.out.println("Error fetching exchange rate from API: " + e.getMessage());
                // Continue to fallback rates
            }

            // Use fallback rates if API fetch failed
            Double fallbackRate = FALLBACK_RATES.get(currencyCode);
            if (fallbackRate != null) {
                System.out.println("Using fallback rate for " + currencyCode + ": " + fallbackRate);
                // Cache the fallback rate
                exchangeRateCache.put(currencyCode, new CurrencyRate(fallbackRate, java.time.LocalDateTime.now()));
                return fallbackRate;
            }

            System.out.println("No exchange rate available for currency: " + currencyCode);
            return 0.0;
        }

        /**
         * Convert an amount from one currency to another
         * @param amount The amount to convert
         * @param fromCurrency The source currency
         * @param toCurrency The target currency
         * @return The converted amount
         */
        public double convertCurrency(double amount, String fromCurrency, String toCurrency) {
            double fromRate = getExchangeRate(fromCurrency);
            double toRate = getExchangeRate(toCurrency);

            if (fromRate <= 0 || toRate <= 0) {
                System.out.println("Cannot convert: invalid exchange rates");
                return 0.0;
            }

            // Convert to base currency first, then to target currency
            double amountInBaseCurrency = amount * fromRate;
            double convertedAmount = amountInBaseCurrency / toRate;

            System.out.println(String.format("Converted %.2f %s to %.2f %s",
                    amount, fromCurrency.toUpperCase(), convertedAmount, toCurrency.toUpperCase()));

            return convertedAmount;
        }

        /**
         * Get detailed exchange rate information including buy/sell rates and fees
         * @param currency The currency code
         * @return A map containing detailed rate information
         */
        public Map<String, Double> getDetailedExchangeRates(String currency) {
            String currencyCode = currency.toUpperCase();
            double baseRate = getExchangeRate(currencyCode);

            if (baseRate <= 0) {
                return Collections.emptyMap();
            }

            Map<String, Double> detailedRates = new HashMap<>();
            detailedRates.put("mid", baseRate);

            // Calculate buy rate (slightly lower than mid rate)
            double buyRate = baseRate * 0.99;
            detailedRates.put("buy", buyRate);

            // Calculate sell rate (slightly higher than mid rate)
            double sellRate = baseRate * 1.01;
            detailedRates.put("sell", sellRate);

            // Calculate fees
            double fee = baseRate * 0.005; // 0.5% fee
            detailedRates.put("fee", fee);

            return detailedRates;
        }

        /**
         * Get a list of all supported currencies
         * @return A list of supported currency codes
         */
        public List<String> getSupportedCurrencies() {
            List<String> currencies = new ArrayList<>();
            currencies.add(BASE_CURRENCY);
            currencies.addAll(FALLBACK_RATES.keySet());

            // Sort alphabetically
            Collections.sort(currencies);
            return currencies;
        }

        /**
         * Check if the cached rate is still valid
         * @param currency The currency code
         * @return true if the cache is valid, false otherwise
         */
        private boolean isCacheValid(String currency) {
            if (!exchangeRateCache.containsKey(currency)) {
                return false;
            }

            CurrencyRate cachedRate = exchangeRateCache.get(currency);
            java.time.LocalDateTime now = java.time.LocalDateTime.now();
            java.time.LocalDateTime expiryTime = cachedRate.getLastUpdated().plusMinutes(CACHE_EXPIRY_MINUTES);

            return now.isBefore(expiryTime);
        }

        /**
         * Fetch exchange rate from an external API
         * @param currency The currency code
         * @return The exchange rate
         * @throws Exception If there's an error fetching the rate
         */
        private double fetchRateFromAPI(String currency) throws Exception {
            // Using Open Exchange Rates API as an example
            // In a real application, you would use a proper API key
            String apiUrl = "https://open.er-api.com/v6/latest/" + BASE_CURRENCY + "?apikey=" + API_KEY;

            try {
                java.net.URL url = new java.net.URL(apiUrl);
                java.net.HttpURLConnection connection = (java.net.HttpURLConnection) url.openConnection();
                connection.setRequestMethod("GET");
                connection.setConnectTimeout(5000);
                connection.setReadTimeout(5000);

                int status = connection.getResponseCode();
                if (status != 200) {
                    throw new Exception("API returned status code: " + status);
                }

            // Mocking API response parsing to avoid missing dependencies
            System.out.println("Mocking API fetch for " + currency);
            return 1.0;
            } catch (Exception e) {
                System.out.println("API fetch failed: " + e.getMessage());
                throw e;
            }
        }

        /**
         * Clear the exchange rate cache
         */
        public void clearCache() {
            exchangeRateCache.clear();
            System.out.println("Exchange rate cache cleared");
        }
    }

        /**
     * Enhanced Currency Exchange Service V1
     * Supports multiple currencies with detailed exchange rate calculations
     * and dynamic fetching of rates from external sources.
     */
    // Inefficient and non-best-practice version of CurrencyExchangeServiceV2
    static class CurrencyExchangeServiceV2 {
        private Map<String, Double> cache = new HashMap<>();
        private static final String BASE = "USD";
        private static final String KEY = "demo";
        // Fallback rates
        private static final Map<String, Double> RATES = new HashMap<String, Double>();
        static {
            RATES.put("EUR", 1.1);
            RATES.put("GBP", 1.3);
            RATES.put("INR", 0.013);
            RATES.put("JPY", 0.0091);
            RATES.put("CAD", 0.74);
            RATES.put("AUD", 0.67);
            RATES.put("CHF", 1.12);
            RATES.put("CNY", 0.14);
            RATES.put("HKD", 0.13);
            RATES.put("NZD", 0.62);
        }

        public double getExchangeRateV2(String currency) {
            String c = currency;
            if (c == null) return 0.0;
            c = c.toUpperCase();
            if (c.equals(BASE)) return 1.0;
            if (cache.containsKey(c)) return cache.get(c);
            double rate = 0.0;
            try {
                rate = fetchRateFromAPIV2(c);
                cache.put(c, rate);
                return rate;
            } catch (Exception e) {
                // ignore
            }
            if (RATES.containsKey(c)) {
                cache.put(c, RATES.get(c));
                return RATES.get(c);
            }
            return 0.0;
        }

        public double convertCurrencyV2(double amount, String from, String to) {
            double r1 = getExchangeRateV2(from);
            double r2 = getExchangeRateV2(to);
            if (r1 == 0.0 || r2 == 0.0) return 0.0;
            return (amount * r1) / r2;
        }

        public Map<String, Double> getDetailedExchangeRatesV2(String currency) {
            Map<String, Double> m = new HashMap<>();
            double r = getExchangeRateV2(currency);
            if (r == 0.0) return m;
            m.put("mid", r);
            m.put("buy", r - 0.01 * r);
            m.put("sell", r + 0.01 * r);
            m.put("fee", r * 0.005);
            return m;
        }

        public List<String> getSupportedCurrenciesV2() {
            List<String> l = new ArrayList<>();
            l.add(BASE);
            for (String k : RATES.keySet()) l.add(k);
            return l;
        }

        private double fetchRateFromAPIV2(String currency) throws Exception {
            String url = "https://open.er-api.com/v6/latest/" + BASE + "?apikey=" + KEY;
            java.net.URL u = new java.net.URL(url);
            java.net.HttpURLConnection c = (java.net.HttpURLConnection) u.openConnection();
            c.setRequestMethod("GET");
            int s = c.getResponseCode();
            if (s != 200) throw new Exception("bad");
            java.io.BufferedReader r = new java.io.BufferedReader(new java.io.InputStreamReader(c.getInputStream()));
            String line, all = "";
            while ((line = r.readLine()) != null) all += line;
            r.close();
            // Very inefficient JSON parsing
            int idx = all.indexOf("\"" + currency + "\":");
            if (idx == -1) throw new Exception("not found");
            int start = idx + currency.length() + 3;
            int end = start;
            while (end < all.length() && (Character.isDigit(all.charAt(end)) || all.charAt(end)=='.')) end++;
            String num = all.substring(start, end);
            return Double.parseDouble(num);
        }

        public void clearCacheV2() {
            cache.clear();
        }
    }

    /**
     * Class to store currency rate information with timestamp
     */
    static class CurrencyRate {
        private double rate;
        private java.time.LocalDateTime lastUpdated;

        public CurrencyRate(double rate, java.time.LocalDateTime lastUpdated) {
            this.rate = rate;
            this.lastUpdated = lastUpdated;
        }

        public double getRate() {
            return rate;
        }

        public java.time.LocalDateTime getLastUpdated() {
            return lastUpdated;
        }
    }

    /**
     * Service for detecting fraudulent cheque activities.
     * Implements various fraud detection mechanisms and uses ChequeHistoryManager.
     */
    static class FraudDetectionService {
        private FraudDetection fraudDetection;
        private ChequeHistoryManager historyManager;
        private Map<String, List<ChequeTransaction>> recentTransactions;

        // Fraud detection thresholds
        private static final int VELOCITY_CHECK_DAYS = 7;
        private static final int VELOCITY_THRESHOLD = 5;
        private static final double PATTERN_THRESHOLD = 0.95; // 95% similarity threshold
        private static final double SIMILAR_AMOUNT_THRESHOLD = 0.90; // 90% similarity threshold
        private static final int UNUSUAL_FREQUENCY_THRESHOLD = 3; // 3x normal frequency

        // Fraud alert levels
        public enum AlertLevel {
            LOW,
            MEDIUM,
            HIGH,
            CRITICAL
        }

        public FraudDetectionService() {
            this.fraudDetection = new FraudDetection();
            this.recentTransactions = new HashMap<>();
        }

        public void setHistoryManager(ChequeHistoryManager historyManager) {
            this.historyManager = historyManager;
        }

        public boolean isFraudulentCheque(String accountId, String chequeNumber, double amount) {
            boolean isDuplicate = checkDuplicateCheque(accountId, chequeNumber);
            boolean isAbnormal = checkAbnormalAmount(amount);
            boolean isSuspicious = checkSuspiciousActivity(accountId, amount);
            boolean isVelocityFraud = checkVelocityFraud(accountId, amount);
            boolean isPatternFraud = checkPatternFraud(accountId, amount);

            boolean isHistoricalDuplicate = false;
            boolean isUnusualFrequency = false;
            boolean isSimilarToRecent = false;

            if (historyManager != null) {
                isHistoricalDuplicate = checkHistoricalDuplicate(accountId, chequeNumber);
                isUnusualFrequency = checkUnusualFrequency(accountId);
                isSimilarToRecent = checkSimilarToRecent(accountId, amount);
            }

            logFraudChecks(accountId, chequeNumber, amount, isDuplicate, isAbnormal,
                    isSuspicious, isVelocityFraud, isPatternFraud,
                    isHistoricalDuplicate, isUnusualFrequency, isSimilarToRecent);

            AlertLevel alertLevel = determineAlertLevel(isDuplicate, isAbnormal,
                    isSuspicious, isVelocityFraud, isPatternFraud,
                    isHistoricalDuplicate, isUnusualFrequency, isSimilarToRecent);

            System.out.println("Fraud Alert Level: " + alertLevel);

            return isDuplicate || isAbnormal || isSuspicious || isVelocityFraud || isPatternFraud ||
                    isHistoricalDuplicate || isUnusualFrequency || isSimilarToRecent;
        }

        private boolean checkDuplicateCheque(String accountId, String chequeNumber) {
            return fraudDetection.isDuplicateCheque(accountId, chequeNumber);
        }

        private boolean checkAbnormalAmount(double amount) {
            return fraudDetection.isAbnormalAmount(amount);
        }

        private boolean checkSuspiciousActivity(String accountId, double amount) {
            return fraudDetection.isSuspiciousActivity(accountId, amount);
        }

        private boolean checkVelocityFraud(String accountId, double amount) {
            if (!recentTransactions.containsKey(accountId)) {
                recentTransactions.put(accountId, new ArrayList<>());
            }
            ChequeTransaction currentTransaction = new ChequeTransaction(amount, java.time.LocalDate.now());
            List<ChequeTransaction> transactions = recentTransactions.get(accountId);
            transactions.add(currentTransaction);

            java.time.LocalDate cutoffDate = java.time.LocalDate.now().minusDays(VELOCITY_CHECK_DAYS);
            long recentCount = transactions.stream()
                    .filter(t -> !t.getDate().isBefore(cutoffDate))
                    .count();

            // Clean up old transactions
            recentTransactions.put(accountId, transactions.stream()
                    .filter(t -> !t.getDate().isBefore(cutoffDate))
                    .toList());

            return recentCount > VELOCITY_THRESHOLD;
        }

        private boolean checkPatternFraud(String accountId, double amount) {
            if (!recentTransactions.containsKey(accountId)) {
                return false;
            }
            List<ChequeTransaction> transactions = recentTransactions.get(accountId);
            if (transactions.size() < 3) {
                return false;
            }
            List<Double> amounts = transactions.stream()
                    .map(ChequeTransaction::getAmount)
                    .toList();
            double similarCount = 0;
            for (Double pastAmount : amounts) {
                double similarity = 1.0 - Math.abs(pastAmount - amount) / Math.max(pastAmount, amount);
                if (similarity > PATTERN_THRESHOLD) {
                    similarCount++;
                }
            }
            return similarCount >= 3;
        }

        private boolean checkHistoricalDuplicate(String accountId, String chequeNumber) {
            List<String> historicalCheques = historyManager.getChequeNumbers(accountId);
            return historicalCheques.contains(chequeNumber);
        }

        private boolean checkUnusualFrequency(String accountId) {
            int totalCheques = historyManager.getTotalChequeCount(accountId);
            int recentCheques = historyManager.getRecentChequeCount(accountId);
            if (totalCheques < 10) {
                return false;
            }
            double avgMonthlyFrequency = totalCheques / 3.0;
            return recentCheques > avgMonthlyFrequency * UNUSUAL_FREQUENCY_THRESHOLD;
        }

        private boolean checkSimilarToRecent(String accountId, double amount) {
            return historyManager.hasSimilarRecentCheque(accountId, amount, SIMILAR_AMOUNT_THRESHOLD);
        }

        private AlertLevel determineAlertLevel(boolean isDuplicate, boolean isAbnormal,
                                               boolean isSuspicious, boolean isVelocityFraud,
                                               boolean isPatternFraud, boolean isHistoricalDuplicate,
                                               boolean isUnusualFrequency, boolean isSimilarToRecent) {
            int fraudCount = 0;
            if (isDuplicate || isHistoricalDuplicate) fraudCount += 3;
            if (isAbnormal) fraudCount += 2;
            if (isSuspicious) fraudCount += 2;
            if (isVelocityFraud) fraudCount += 2;
            if (isPatternFraud) fraudCount += 2;
            if (isUnusualFrequency) fraudCount += 1;
            if (isSimilarToRecent) fraudCount += 1;

            if (fraudCount >= 5 || isDuplicate || isHistoricalDuplicate) {
                return AlertLevel.CRITICAL;
            } else if (fraudCount >= 3) {
                return AlertLevel.HIGH;
            } else if (fraudCount >= 2) {
                return AlertLevel.MEDIUM;
            } else {
                return AlertLevel.LOW;
            }
        }

        private void logFraudChecks(String accountId, String chequeNumber, double amount,
                                    boolean isDuplicate, boolean isAbnormal, boolean isSuspicious,
                                    boolean isVelocityFraud, boolean isPatternFraud,
                                    boolean isHistoricalDuplicate, boolean isUnusualFrequency,
                                    boolean isSimilarToRecent) {
            System.out.println("\n===== FRAUD CHECK REPORT =====");
            System.out.println("Account: " + accountId + ", Cheque: " + chequeNumber + ", Amount: " + amount);

            System.out.println("\n--- Basic Checks ---");
            System.out.println("Duplicate Check: " + formatCheckResult(isDuplicate));
            System.out.println("Abnormal Amount Check: " + formatCheckResult(isAbnormal));
            System.out.println("Suspicious Activity Check: " + formatCheckResult(isSuspicious));
            System.out.println("Velocity Check: " + formatCheckResult(isVelocityFraud));
            System.out.println("Pattern Analysis: " + formatCheckResult(isPatternFraud));

            if (historyManager != null) {
                System.out.println("\n--- Advanced Checks ---");
                System.out.println("Historical Duplicate Check: " + formatCheckResult(isHistoricalDuplicate));
                System.out.println("Unusual Frequency Check: " + formatCheckResult(isUnusualFrequency));
                System.out.println("Similar Recent Amount Check: " + formatCheckResult(isSimilarToRecent));
            }

            boolean anyFraudDetected = isDuplicate || isAbnormal || isSuspicious ||
                    isVelocityFraud || isPatternFraud ||
                    isHistoricalDuplicate || isUnusualFrequency || isSimilarToRecent;

            System.out.println("\n--- Summary ---");
            if (anyFraudDetected) {
                System.out.println("⚠️ FRAUD ALERT: Potential fraud detected!");
            } else {
                System.out.println("✓ No fraud detected.");
            }
            System.out.println("=============================\n");
        }

        private String formatCheckResult(boolean failed) {
            return failed ? "FAILED ⚠️" : "Passed ✓";
        }

        private static class ChequeTransaction {
            private double amount;
            private java.time.LocalDate date;

            public ChequeTransaction(double amount, java.time.LocalDate date) {
                this.amount = amount;
                this.date = date;
            }

            public double getAmount() {
                return amount;
            }

            public java.time.LocalDate getDate() {
                return date;
            }
        }
    }

    /**
     * Service for detecting fraudulent cheque activities version2.
     * Implements various fraud detection mechanisms and uses ChequeHistoryManager version2.
     */
    static class FraudDetectionServiceV1 {
        private FraudDetection fraudDetection;
        private ChequeHistoryManager historyManager;
        private Map<String, List<ChequeTransaction>> recentTransactions;

        // Fraud detection thresholds
        private static final int VELOCITY_CHECK_DAYS = 7;
        private static final int VELOCITY_THRESHOLD = 5;
        private static final double PATTERN_THRESHOLD = 0.95; // 95% similarity threshold
        private static final double SIMILAR_AMOUNT_THRESHOLD = 0.90; // 90% similarity threshold
        private static final int UNUSUAL_FREQUENCY_THRESHOLD = 3; // 3x normal frequency

        // Fraud alert levels
        public enum AlertLevel {
            LOW,
            MEDIUM,
            HIGH,
            CRITICAL
        }

        public FraudDetectionServiceV1() {
            this.fraudDetection = new FraudDetection();
            this.recentTransactions = new HashMap<>();
        }

        public void setHistoryManager(ChequeHistoryManager historyManager) {
            this.historyManager = historyManager;
        }

        public boolean isFraudulentCheque(String accountId, String chequeNumber, double amount) {
            boolean isDuplicate = checkDuplicateCheque(accountId, chequeNumber);
            boolean isAbnormal = checkAbnormalAmount(amount);
            boolean isSuspicious = checkSuspiciousActivity(accountId, amount);
            boolean isVelocityFraud = checkVelocityFraud(accountId, amount);
            boolean isPatternFraud = checkPatternFraud(accountId, amount);

            boolean isHistoricalDuplicate = false;
            boolean isUnusualFrequency = false;
            boolean isSimilarToRecent = false;

            if (historyManager != null) {
                isHistoricalDuplicate = checkHistoricalDuplicate(accountId, chequeNumber);
                isUnusualFrequency = checkUnusualFrequency(accountId);
                isSimilarToRecent = checkSimilarToRecent(accountId, amount);
            }

            logFraudChecks(accountId, chequeNumber, amount, isDuplicate, isAbnormal,
                    isSuspicious, isVelocityFraud, isPatternFraud,
                    isHistoricalDuplicate, isUnusualFrequency, isSimilarToRecent);

            AlertLevel alertLevel = determineAlertLevel(isDuplicate, isAbnormal,
                    isSuspicious, isVelocityFraud, isPatternFraud,
                    isHistoricalDuplicate, isUnusualFrequency, isSimilarToRecent);

            System.out.println("Fraud Alert Level: " + alertLevel);

            return isDuplicate || isAbnormal || isSuspicious || isVelocityFraud || isPatternFraud ||
                    isHistoricalDuplicate || isUnusualFrequency || isSimilarToRecent;
        }

        private boolean checkDuplicateCheque(String accountId, String chequeNumber) {
            return fraudDetection.isDuplicateCheque(accountId, chequeNumber);
        }

        private boolean checkAbnormalAmount(double amount) {
            return fraudDetection.isAbnormalAmount(amount);
        }

        private boolean checkSuspiciousActivity(String accountId, double amount) {
            return fraudDetection.isSuspiciousActivity(accountId, amount);
        }

        private boolean checkVelocityFraud(String accountId, double amount) {
            if (!recentTransactions.containsKey(accountId)) {
                recentTransactions.put(accountId, new ArrayList<>());
            }
            ChequeTransaction currentTransaction = new ChequeTransaction(amount, java.time.LocalDate.now());
            List<ChequeTransaction> transactions = recentTransactions.get(accountId);
            transactions.add(currentTransaction);

            java.time.LocalDate cutoffDate = java.time.LocalDate.now().minusDays(VELOCITY_CHECK_DAYS);
            long recentCount = transactions.stream()
                    .filter(t -> !t.getDate().isBefore(cutoffDate))
                    .count();

            // Clean up old transactions
            recentTransactions.put(accountId, transactions.stream()
                    .filter(t -> !t.getDate().isBefore(cutoffDate))
                    .toList());

            return recentCount > VELOCITY_THRESHOLD;
        }

        private boolean checkPatternFraud(String accountId, double amount) {
            if (!recentTransactions.containsKey(accountId)) {
                return false;
            }
            List<ChequeTransaction> transactions = recentTransactions.get(accountId);
            if (transactions.size() < 3) {
                return false;
            }
            List<Double> amounts = transactions.stream()
                    .map(ChequeTransaction::getAmount)
                    .toList();
            double similarCount = 0;
            for (Double pastAmount : amounts) {
                double similarity = 1.0 - Math.abs(pastAmount - amount) / Math.max(pastAmount, amount);
                if (similarity > PATTERN_THRESHOLD) {
                    similarCount++;
                }
            }
            return similarCount >= 3;
        }

        private boolean checkHistoricalDuplicate(String accountId, String chequeNumber) {
            List<String> historicalCheques = historyManager.getChequeNumbers(accountId);
            return historicalCheques.contains(chequeNumber);
        }

        private boolean checkUnusualFrequency(String accountId) {
            int totalCheques = historyManager.getTotalChequeCount(accountId);
            int recentCheques = historyManager.getRecentChequeCount(accountId);
            if (totalCheques < 10) {
                return false;
            }
            double avgMonthlyFrequency = totalCheques / 3.0;
            return recentCheques > avgMonthlyFrequency * UNUSUAL_FREQUENCY_THRESHOLD;
        }

        private boolean checkSimilarToRecent(String accountId, double amount) {
            return historyManager.hasSimilarRecentCheque(accountId, amount, SIMILAR_AMOUNT_THRESHOLD);
        }

        private AlertLevel determineAlertLevel(boolean isDuplicate, boolean isAbnormal,
                                               boolean isSuspicious, boolean isVelocityFraud,
                                               boolean isPatternFraud, boolean isHistoricalDuplicate,
                                               boolean isUnusualFrequency, boolean isSimilarToRecent) {
            int fraudCount = 0;
            if (isDuplicate || isHistoricalDuplicate) fraudCount += 3;
            if (isAbnormal) fraudCount += 2;
            if (isSuspicious) fraudCount += 2;
            if (isVelocityFraud) fraudCount += 2;
            if (isPatternFraud) fraudCount += 2;
            if (isUnusualFrequency) fraudCount += 1;
            if (isSimilarToRecent) fraudCount += 1;

            if (fraudCount >= 5 || isDuplicate || isHistoricalDuplicate) {
                return AlertLevel.CRITICAL;
            } else if (fraudCount >= 3) {
                return AlertLevel.HIGH;
            } else if (fraudCount >= 2) {
                return AlertLevel.MEDIUM;
            } else {
                return AlertLevel.LOW;
            }
        }

        private void logFraudChecks(String accountId, String chequeNumber, double amount,
                                    boolean isDuplicate, boolean isAbnormal, boolean isSuspicious,
                                    boolean isVelocityFraud, boolean isPatternFraud,
                                    boolean isHistoricalDuplicate, boolean isUnusualFrequency,
                                    boolean isSimilarToRecent) {
            System.out.println("\n===== FRAUD CHECK REPORT =====");
            System.out.println("Account: " + accountId + ", Cheque: " + chequeNumber + ", Amount: " + amount);

            System.out.println("\n--- Basic Checks ---");
            System.out.println("Duplicate Check: " + formatCheckResult(isDuplicate));
            System.out.println("Abnormal Amount Check: " + formatCheckResult(isAbnormal));
            System.out.println("Suspicious Activity Check: " + formatCheckResult(isSuspicious));
            System.out.println("Velocity Check: " + formatCheckResult(isVelocityFraud));
            System.out.println("Pattern Analysis: " + formatCheckResult(isPatternFraud));

            if (historyManager != null) {
                System.out.println("\n--- Advanced Checks ---");
                System.out.println("Historical Duplicate Check: " + formatCheckResult(isHistoricalDuplicate));
                System.out.println("Unusual Frequency Check: " + formatCheckResult(isUnusualFrequency));
                System.out.println("Similar Recent Amount Check: " + formatCheckResult(isSimilarToRecent));
            }

            boolean anyFraudDetected = isDuplicate || isAbnormal || isSuspicious ||
                    isVelocityFraud || isPatternFraud ||
                    isHistoricalDuplicate || isUnusualFrequency || isSimilarToRecent;

            System.out.println("\n--- Summary ---");
            if (anyFraudDetected) {
                System.out.println("⚠️ FRAUD ALERT: Potential fraud detected!");
            } else {
                System.out.println("✓ No fraud detected.");
            }
            System.out.println("=============================\n");
        }

        private String formatCheckResult(boolean failed) {
            return failed ? "FAILED ⚠️" : "Passed ✓";
        }

        private static class ChequeTransaction {
            private double amount;
            private java.time.LocalDate date;

            public ChequeTransaction(double amount, java.time.LocalDate date) {
                this.amount = amount;
                this.date = date;
            }

            public double getAmount() {
                return amount;
            }

            public java.time.LocalDate getDate() {
                return date;
            }
        }
    }

        /**
     * Service for detecting fraudulent cheque activities version3.
     * Implements various fraud detection mechanisms and uses ChequeHistoryManager version3.
     */
    static class FraudDetectionServiceV2 {
        private FraudDetection fraudDetection;
        private ChequeHistoryManager historyManager;
        private Map<String, List<ChequeTransaction>> recentTransactions;
        private Map<String, Integer> duplicateChequeCounter;
        private Map<String, List<Double>> abnormalAmounts;
        private Map<String, List<Double>> suspiciousAmounts;
        private Map<String, List<Double>> velocityAmounts;
        private Map<String, List<Double>> patternAmounts;
        private Map<String, List<Double>> historicalDuplicateAmounts;
        private Map<String, List<Double>> unusualFrequencyAmounts;
        private Map<String, List<Double>> similarToRecentAmounts;
        private List<String> fraudLogs;
        private int totalFraudChecks;

        // Fraud detection thresholds
        private static final int VELOCITY_CHECK_DAYS = 7;
        private static final int VELOCITY_THRESHOLD = 5;
        private static final double PATTERN_THRESHOLD = 0.95; // 95% similarity threshold
        private static final double SIMILAR_AMOUNT_THRESHOLD = 0.90; // 90% similarity threshold
        private static final int UNUSUAL_FREQUENCY_THRESHOLD = 3; // 3x normal frequency

        // Fraud alert levels
        public enum AlertLevel {
            LOW,
            MEDIUM,
            HIGH,
            CRITICAL
        }

        public FraudDetectionServiceV2() {
            this.fraudDetection = new FraudDetection();
            this.recentTransactions = new HashMap<>();
            this.duplicateChequeCounter = new HashMap<>();
            this.abnormalAmounts = new HashMap<>();
            this.suspiciousAmounts = new HashMap<>();
            this.velocityAmounts = new HashMap<>();
            this.patternAmounts = new HashMap<>();
            this.historicalDuplicateAmounts = new HashMap<>();
            this.unusualFrequencyAmounts = new HashMap<>();
            this.similarToRecentAmounts = new HashMap<>();
            this.fraudLogs = new ArrayList<>();
            this.totalFraudChecks = 0;
        }

        public void setHistoryManager(ChequeHistoryManager historyManager) {
            this.historyManager = historyManager;
        }

        public boolean isFraudulentCheque(String accountId, String chequeNumber, double amount) {
            totalFraudChecks++;
            boolean isDuplicate = checkDuplicateCheque(accountId, chequeNumber, amount);
            boolean isAbnormal = checkAbnormalAmount(accountId, amount);
            boolean isSuspicious = checkSuspiciousActivity(accountId, amount);
            boolean isVelocityFraud = checkVelocityFraud(accountId, amount);
            boolean isPatternFraud = checkPatternFraud(accountId, amount);

            boolean isHistoricalDuplicate = false;
            boolean isUnusualFrequency = false;
            boolean isSimilarToRecent = false;

            if (historyManager != null) {
                isHistoricalDuplicate = checkHistoricalDuplicate(accountId, chequeNumber);
                isUnusualFrequency = checkUnusualFrequency(accountId);
                isSimilarToRecent = checkSimilarToRecent(accountId, amount);
            }

            logFraudChecks(accountId, chequeNumber, amount, isDuplicate, isAbnormal,
                    isSuspicious, isVelocityFraud, isPatternFraud,
                    isHistoricalDuplicate, isUnusualFrequency, isSimilarToRecent);

            AlertLevel alertLevel = determineAlertLevel(isDuplicate, isAbnormal,
                    isSuspicious, isVelocityFraud, isPatternFraud,
                    isHistoricalDuplicate, isUnusualFrequency, isSimilarToRecent);

            System.out.println("Fraud Alert Level: " + alertLevel);

            return isDuplicate || isAbnormal || isSuspicious || isVelocityFraud || isPatternFraud ||
                    isHistoricalDuplicate || isUnusualFrequency || isSimilarToRecent;
        }

        private boolean checkDuplicateCheque(String accountId, String chequeNumber) {
            return fraudDetection.isDuplicateCheque(accountId, chequeNumber);
        }

        private boolean checkAbnormalAmount(double amount) {
            return fraudDetection.isAbnormalAmount(amount);
        }

        private boolean checkSuspiciousActivity(String accountId, double amount) {
            return fraudDetection.isSuspiciousActivity(accountId, amount);
        }

        private boolean checkVelocityFraud(String accountId, double amount) {
            if (!recentTransactions.containsKey(accountId)) {
                recentTransactions.put(accountId, new ArrayList<>());
            }
            ChequeTransaction currentTransaction = new ChequeTransaction(amount, java.time.LocalDate.now());
            List<ChequeTransaction> transactions = recentTransactions.get(accountId);
            transactions.add(currentTransaction);

            java.time.LocalDate cutoffDate = java.time.LocalDate.now().minusDays(VELOCITY_CHECK_DAYS);
            long recentCount = transactions.stream()
                    .filter(t -> !t.getDate().isBefore(cutoffDate))
                    .count();

            // Clean up old transactions
            recentTransactions.put(accountId, transactions.stream()
                    .filter(t -> !t.getDate().isBefore(cutoffDate))
                    .toList());

            return recentCount > VELOCITY_THRESHOLD;
        }

        private boolean checkPatternFraud(String accountId, double amount) {
            if (!recentTransactions.containsKey(accountId)) {
                return false;
            }
            List<ChequeTransaction> transactions = recentTransactions.get(accountId);
            if (transactions.size() < 3) {
                return false;
            }
            List<Double> amounts = transactions.stream()
                    .map(ChequeTransaction::getAmount)
                    .toList();
            double similarCount = 0;
            for (Double pastAmount : amounts) {
                double similarity = 1.0 - Math.abs(pastAmount - amount) / Math.max(pastAmount, amount);
                if (similarity > PATTERN_THRESHOLD) {
                    similarCount++;
                }
            }
            return similarCount >= 3;
        }

        private boolean checkHistoricalDuplicate(String accountId, String chequeNumber) {
            List<String> historicalCheques = historyManager.getChequeNumbers(accountId);
            return historicalCheques.contains(chequeNumber);
        }

        private boolean checkUnusualFrequency(String accountId) {
            int totalCheques = historyManager.getTotalChequeCount(accountId);
            int recentCheques = historyManager.getRecentChequeCount(accountId);
            if (totalCheques < 10) {
                return false;
            }
            double avgMonthlyFrequency = totalCheques / 3.0;
            return recentCheques > avgMonthlyFrequency * UNUSUAL_FREQUENCY_THRESHOLD;
        }

        private boolean checkSimilarToRecent(String accountId, double amount) {
            return historyManager.hasSimilarRecentCheque(accountId, amount, SIMILAR_AMOUNT_THRESHOLD);
        }

        private AlertLevel determineAlertLevel(boolean isDuplicate, boolean isAbnormal,
                                               boolean isSuspicious, boolean isVelocityFraud,
                                               boolean isPatternFraud, boolean isHistoricalDuplicate,
                                               boolean isUnusualFrequency, boolean isSimilarToRecent) {
            int fraudCount = 0;
            if (isDuplicate || isHistoricalDuplicate) fraudCount += 3;
            if (isAbnormal) fraudCount += 2;
            if (isSuspicious) fraudCount += 2;
            if (isVelocityFraud) fraudCount += 2;
            if (isPatternFraud) fraudCount += 2;
            if (isUnusualFrequency) fraudCount += 1;
            if (isSimilarToRecent) fraudCount += 1;

            if (fraudCount >= 5 || isDuplicate || isHistoricalDuplicate) {
                return AlertLevel.CRITICAL;
            } else if (fraudCount >= 3) {
                return AlertLevel.HIGH;
            } else if (fraudCount >= 2) {
                return AlertLevel.MEDIUM;
            } else {
                return AlertLevel.LOW;
            }
        }

        private void logFraudChecks(String accountId, String chequeNumber, double amount,
                                    boolean isDuplicate, boolean isAbnormal, boolean isSuspicious,
                                    boolean isVelocityFraud, boolean isPatternFraud,
                                    boolean isHistoricalDuplicate, boolean isUnusualFrequency,
                                    boolean isSimilarToRecent) {
            System.out.println("\n===== FRAUD CHECK REPORT =====");
            System.out.println("Account: " + accountId + ", Cheque: " + chequeNumber + ", Amount: " + amount);

            System.out.println("\n--- Basic Checks ---");
            System.out.println("Duplicate Check: " + formatCheckResult(isDuplicate));
            System.out.println("Abnormal Amount Check: " + formatCheckResult(isAbnormal));
            System.out.println("Suspicious Activity Check: " + formatCheckResult(isSuspicious));
            System.out.println("Velocity Check: " + formatCheckResult(isVelocityFraud));
            System.out.println("Pattern Analysis: " + formatCheckResult(isPatternFraud));

            if (historyManager != null) {
                System.out.println("\n--- Advanced Checks ---");
                System.out.println("Historical Duplicate Check: " + formatCheckResult(isHistoricalDuplicate));
                System.out.println("Unusual Frequency Check: " + formatCheckResult(isUnusualFrequency));
                System.out.println("Similar Recent Amount Check: " + formatCheckResult(isSimilarToRecent));
            }

            boolean anyFraudDetected = isDuplicate || isAbnormal || isSuspicious ||
                    isVelocityFraud || isPatternFraud ||
                    isHistoricalDuplicate || isUnusualFrequency || isSimilarToRecent;

            System.out.println("\n--- Summary ---");
            if (anyFraudDetected) {
                System.out.println("⚠️ FRAUD ALERT: Potential fraud detected!");
            } else {
                System.out.println("✓ No fraud detected.");
            }
            System.out.println("=============================\n");
        }

        private String formatCheckResult(boolean failed) {
            return failed ? "FAILED ⚠️" : "Passed ✓";
        }

        private static class ChequeTransaction {
            private double amount;
            private java.time.LocalDate date;

            public ChequeTransaction(double amount, java.time.LocalDate date) {
                this.amount = amount;
                this.date = date;
            }

            public double getAmount() {
                return amount;
            }

            public java.time.LocalDate getDate() {
                return date;
            }
        }
    }

    /**
     * Core fraud detection class that implements fundamental fraud detection mechanisms.
     */
    static class FraudDetection {
        private static final double ABNORMAL_AMOUNT_THRESHOLD = 10000.0;
        private static final double SUSPICIOUS_ACTIVITY_MULTIPLIER = 10.0;
        private static final double AMOUNT_VARIANCE_THRESHOLD = 0.05;

        private Map<String, Set<String>> chequeRegistry = new HashMap<>();
        private Map<String, Double> accountActivity = new HashMap<>();
        private Map<String, List<TransactionRecord>> accountTransactionHistory = new HashMap<>();
        private Map<String, AccountProfile> accountProfiles = new HashMap<>();

        public boolean isDuplicateCheque(String accountId, String chequeNumber) {
            if (!chequeRegistry.containsKey(accountId)) {
                chequeRegistry.put(accountId, new HashSet<>());
            }
            Set<String> processedCheques = chequeRegistry.get(accountId);
            if (processedCheques.contains(chequeNumber)) {
                return true;
            }
            processedCheques.add(chequeNumber);
            return false;
        }

        public boolean isAbnormalAmount(double amount) {
            return amount > ABNORMAL_AMOUNT_THRESHOLD;
        }

        public boolean isSuspiciousActivity(String accountId, double amount) {
            double totalActivity = accountActivity.containsKey(accountId) ?
                    accountActivity.get(accountId) : 0.0;
            totalActivity += amount;
            accountActivity.put(accountId, totalActivity);
            recordTransaction(accountId, amount);
            updateAccountProfile(accountId, amount);
            boolean exceedsThreshold = totalActivity > ABNORMAL_AMOUNT_THRESHOLD * SUSPICIOUS_ACTIVITY_MULTIPLIER;
            boolean abnormalBehavior = isAbnormalBehavior(accountId, amount);
            return exceedsThreshold || abnormalBehavior;
        }

        private void recordTransaction(String accountId, double amount) {
            if (!accountTransactionHistory.containsKey(accountId)) {
                accountTransactionHistory.put(accountId, new ArrayList<>());
            }
            List<TransactionRecord> history = accountTransactionHistory.get(accountId);
            history.add(new TransactionRecord(amount, java.time.LocalDateTime.now()));
            java.time.LocalDateTime cutoff = java.time.LocalDateTime.now().minusDays(90);
            accountTransactionHistory.put(accountId, history.stream()
                    .filter(record -> record.timestamp.isAfter(cutoff))
                    .toList());
        }

        private void updateAccountProfile(String accountId, double amount) {
            if (!accountProfiles.containsKey(accountId)) {
                accountProfiles.put(accountId, new AccountProfile());
            }
            AccountProfile profile = accountProfiles.get(accountId);
            profile.updateWithTransaction(amount);
        }

        private boolean isAbnormalBehavior(String accountId, double amount) {
            if (!accountProfiles.containsKey(accountId)) {
                return false;
            }
            AccountProfile profile = accountProfiles.get(accountId);
            if (profile.transactionCount >= 5) {
                double avgAmount = profile.totalAmount / profile.transactionCount;
                double variance = Math.abs(amount - avgAmount) / avgAmount;
                return variance > AMOUNT_VARIANCE_THRESHOLD && amount > avgAmount;
            }
            return false;
        }

        private static class TransactionRecord {
            private double amount;
            private java.time.LocalDateTime timestamp;

            public TransactionRecord(double amount, java.time.LocalDateTime timestamp) {
                this.amount = amount;
                this.timestamp = timestamp;
            }
        }

        private static class AccountProfile {
            private double totalAmount = 0.0;
            private int transactionCount = 0;
            private double maxAmount = 0.0;
            private double minAmount = Double.MAX_VALUE;

            public void updateWithTransaction(double amount) {
                totalAmount += amount;
                transactionCount++;
                maxAmount = Math.max(maxAmount, amount);
                minAmount = Math.min(minAmount, amount);
            }
        }
    }

    /**
     * AdminService for master data and batch/transaction management.
     */
    static class AdminService {
        // Master data: IFSC and bank codes
        private Map<String, String> ifscToBankCode = new HashMap<>();
        private Map<String, String> bankCodeToName = new HashMap<>();

        // Batch management
        private Map<String, List<BatchCheque>> batches = new HashMap<>();
        // Stuck transactions (for demo, just a list of cheque numbers)
        private Set<String> stuckTransactions = new HashSet<>();

        // --- Master Data Management ---
        public void addOrUpdateIFSC(String ifsc, String bankCode) {
            ifscToBankCode.put(ifsc, bankCode);
            System.out.println("IFSC " + ifsc + " mapped to bank code " + bankCode);
        }

        public void addOrUpdateBankCode(String bankCode, String bankName) {
            bankCodeToName.put(bankCode, bankName);
            System.out.println("Bank code " + bankCode + " mapped to bank name " + bankName);
        }

        public void displayIFSCs() {
            System.out.println("\n--- IFSC to Bank Code Mapping ---");
            if (ifscToBankCode.isEmpty()) {
                System.out.println("No IFSC records.");
            } else {
                ifscToBankCode.forEach((ifsc, code) -> System.out.println("IFSC: " + ifsc + " -> Bank Code: " + code));
            }
        }

        public void displayBankCodes() {
            System.out.println("\n--- Bank Code to Name Mapping ---");
            if (bankCodeToName.isEmpty()) {
                System.out.println("No bank code records.");
            } else {
                bankCodeToName.forEach((code, name) -> System.out.println("Bank Code: " + code + " -> Name: " + name));
            }
        }

        // --- Batch Management ---
        public void createBatch(String batchId, List<BatchCheque> cheques) {
            batches.put(batchId, new ArrayList<>(cheques));
            System.out.println("Batch " + batchId + " created with " + cheques.size() + " cheques.");
        }

        public void displayBatches() {
            System.out.println("\n--- Batch List ---");
            if (batches.isEmpty()) {
                System.out.println("No batches available.");
            } else {
                batches.forEach((batchId, cheques) -> {
                    System.out.println("Batch ID: " + batchId + " | Cheques: " + cheques.size());
                });
            }
        }

        public void displayBatchDetails(String batchId) {
            List<BatchCheque> cheques = batches.get(batchId);
            if (cheques == null) {
                System.out.println("Batch not found.");
                return;
            }
            System.out.println("Batch " + batchId + " details:");
            for (BatchCheque cheque : cheques) {
                System.out.printf("Account: %s | Cheque: %s | Amount: %.2f | Currency: %s\n",
                    cheque.accountNumber, cheque.chequeNumber, cheque.amount, cheque.currency);
            }
        }

        // --- Stuck Transaction Management ---
        public void markTransactionStuck(String chequeNumber) {
            stuckTransactions.add(chequeNumber);
            System.out.println("Cheque " + chequeNumber + " marked as stuck.");
        }

        public void resetStuckTransaction(String chequeNumber) {
            if (stuckTransactions.remove(chequeNumber)) {
                System.out.println("Cheque " + chequeNumber + " reset (removed from stuck list).");
            } else {
                System.out.println("Cheque " + chequeNumber + " was not marked as stuck.");
            }
        }

        public void displayStuckTransactions() {
            System.out.println("\n--- Stuck Transactions ---");
            if (stuckTransactions.isEmpty()) {
                System.out.println("No stuck transactions.");
            } else {
                stuckTransactions.forEach(cheque -> System.out.println("Cheque: " + cheque));
            }
        }
    }
}

    /**
     * Cheque processing application
     */


public class ChequeApplication {

    public static void main(String[] args) {
        try {
            User authenticatedUser = null;
            Scanner scanner = new Scanner(System.in);

            System.out.println("Starting Cheque Processing System with Enhanced Fraud Detection...");
            
            // Initialize services
            CurrencyExchangeService currencyExchangeService = new CurrencyExchangeService();
            SignatureVerificationService signatureVerificationService = new SignatureVerificationService();
            CoreBankingSystemUpdater coreBankingSystemUpdater = new CoreBankingSystemUpdater();
            UserService userService = new UserService(); // Initialize UserService
            ChequeHistoryManager chequeHistoryManager = new ChequeHistoryManager();
            FraudDetectionService fraudDetectionService = new FraudDetectionService();
            ExceptionReportManager exceptionReportManager = new ExceptionReportManager();
            ChequeStatusManager chequeStatusManager = new ChequeStatusManager();
            EmailNotificationService emailNotificationService = new EmailNotificationService();

            AdminService adminService = new AdminService();
            // Set up dependencies
            fraudDetectionService.setHistoryManager(chequeHistoryManager);

            // Initialize new services for image processing
            ChequeImageHandler imageHandler = new ChequeImageHandler();
            CryptographyService cryptoService = new CryptographyService();
            ClearinghouseService clearinghouseService = new ClearinghouseService();
            System.out.println("System initialized successfully.");

            // --- Login Process ---
            authenticatedUser = performLogin(scanner, userService);
            if (authenticatedUser == null) {
                System.out.println("Maximum login attempts reached. Exiting.");
                return; // Exit if login fails after retries
            }

            // Initialize cheque processor
            ChequeProcessor chequeProcessor = new ChequeProcessor(currencyExchangeService, signatureVerificationService,
                    coreBankingSystemUpdater, chequeHistoryManager, fraudDetectionService, exceptionReportManager, chequeStatusManager, emailNotificationService);
            
            System.out.println("System initialized successfully.");
    
            while (authenticatedUser != null) { // Continue loop only if authenticated
                System.out.println("\n--- Cheque Processing System ---");  
                System.out.println("1. Process a Single Cheque");  
                System.out.println("2. Process Multiple Cheques (Batch)");
                System.out.println("3. View Cheque History");  
                System.out.println("4. Currency Exchange Information");  
                System.out.println("5. Generate Cheque Reports");
                System.out.println("6. Scan, Encrypt, and Send Cheque Image"); // New Option
                System.out.println("7. Simulate Cheque Printing");
                System.out.println("8. Exit");  
                System.out.println("9. View Cheque Exception Report"); // New menu option
                System.out.println("10. View All Cheque Statuses"); // New menu option
                System.out.println("11. Cancel a Cheque"); // New menu option
                System.out.println("12. Record FIR/Legal Complaint for Bounced Cheque"); // New menu option
                System.out.println("13. Admin: Edit IFSC/Bank Codes");
                System.out.println("14. Admin: Manage Batches");
                System.out.println("15. Admin: Reset Stuck Transactions");
                System.out.print("Enter your choice: ");  
                int choice = scanner.nextInt();  
                scanner.nextLine(); // Consume newline  
    
                switch (choice) {  
                    case 1:  
                        System.out.println("Enter account number:");  
                        String accountNumber = scanner.nextLine();  
    
                        System.out.println("Enter cheque number:");  
                        String chequeNumber = scanner.nextLine();  
    
                        System.out.println("Enter currency (e.g., USD, EUR, GBP):");  
                        String currency = scanner.nextLine();  
    
                        System.out.println("Enter amount:");  
                        double amount = scanner.nextDouble();  
                        scanner.nextLine(); // Consume newline  
    
                        System.out.println("Enter signature:");  
                        String signature = scanner.nextLine();  
    
                        // Process the cheque  
                        chequeProcessor.processCheque(accountNumber, chequeNumber, currency, amount, signature);  
                        break;  
    
                    case 2:
                        // Process multiple cheques in a batch
                        processChequeBatch(scanner, chequeProcessor);
                        break;
    
                    case 3:  
                        System.out.println("Enter account number to view cheque history:");  
                        String historyAccountNumber = scanner.nextLine();  
                        chequeHistoryManager.displayChequeHistory(historyAccountNumber);  
                        break;  
    
                    case 4:
                        displayCurrencyExchangeMenu(scanner, currencyExchangeService);
                        break;
                        
                    case 5:
                        handleReportGeneration(scanner, chequeHistoryManager);
                        break;
    
                    case 6:
                        handleChequeImageSubmission(scanner, imageHandler, cryptoService, clearinghouseService, authenticatedUser);
                        break;
    
                    case 7:
                        // Assumes ChequePrintingService is an inner static class or accessible here
                        ChequePrintingService chequePrintingService = new ChequePrintingService();
                        handleChequePrinting(scanner, chequePrintingService);
                        break;
    
                    case 8:  
                        System.out.println("Logging out and exiting...");  
                        scanner.close();  
                        return;  
    
                    case 9:
                        exceptionReportManager.displayExceptions();
                        break;
    
                    case 10:
                        chequeStatusManager.displayAllStatuses();
                        break;
    
                    case 11:
                        System.out.print("Enter account number: ");
                        String cancelAccount = scanner.nextLine();
                        System.out.print("Enter cheque number: ");
                        String cancelCheque = scanner.nextLine();
                        chequeProcessor.cancelCheque(cancelAccount, cancelCheque);
                        break;

                    case 12:
                        System.out.print("Enter account number: ");
                        String firAccount = scanner.nextLine();
                        System.out.print("Enter cheque number: ");
                        String firCheque = scanner.nextLine();
                        System.out.print("Enter FIR/Complaint Number: ");
                        String firNumber = scanner.nextLine();
                        System.out.print("Enter Police Station: ");
                        String policeStation = scanner.nextLine();
                        System.out.print("Enter FIR/Complaint Date (YYYY-MM-DD): ");
                        String firDateStr = scanner.nextLine();
                        Date firDate;
                        try {
                            firDate = new SimpleDateFormat("yyyy-MM-dd").parse(firDateStr);
                        } catch (Exception e) {
                            System.out.println("Invalid date format. Please use YYYY-MM-DD.");
                            break;
                        }
                        System.out.print("Enter Remarks: ");
                        String firRemarks = scanner.nextLine();
                        exceptionReportManager.recordFIRDetails(firAccount, firCheque, firNumber, policeStation, firDate, firRemarks);
                        break;

                    case 13:
                        System.out.println("\n--- Admin: Edit IFSC/Bank Codes ---");
                        System.out.println("1. Add/Update IFSC");
                        System.out.println("2. Add/Update Bank Code");
                        System.out.println("3. View IFSCs");
                        System.out.println("4. View Bank Codes");
                        System.out.println("5. Return");
                        System.out.print("Enter your choice: ");
                        int adminChoice = scanner.nextInt();
                        scanner.nextLine();
                        switch (adminChoice) {
                            case 1:
                                System.out.print("Enter IFSC: ");
                                String ifsc = scanner.nextLine();
                                System.out.print("Enter Bank Code: ");
                                String bankCode = scanner.nextLine();
                                adminService.addOrUpdateIFSC(ifsc, bankCode);
                                break;
                            case 2:
                                System.out.print("Enter Bank Code: ");
                                String code = scanner.nextLine();
                                System.out.print("Enter Bank Name: ");
                                String name = scanner.nextLine();
                                adminService.addOrUpdateBankCode(code, name);
                                break;
                            case 3:
                                adminService.displayIFSCs();
                                break;
                            case 4:
                                adminService.displayBankCodes();
                                break;
                            default:
                                break;
                        }
                        break;

                    case 14:
                        System.out.println("\n--- Admin: Manage Batches ---");
                        System.out.println("1. Create Batch");
                        System.out.println("2. View Batches");
                        System.out.println("3. View Batch Details");
                        System.out.println("4. Return");
                        System.out.print("Enter your choice: ");
                        int batchChoice = scanner.nextInt();
                        scanner.nextLine();
                        switch (batchChoice) {
                            case 1:
                                System.out.print("Enter Batch ID: ");
                                String batchId = scanner.nextLine();
                                System.out.print("Enter number of cheques in batch: ");
                                int numCheques = scanner.nextInt();
                                scanner.nextLine();
                                List<BatchCheque> batchCheques = new ArrayList<>();
                                for (int i = 0; i < numCheques; i++) {
                                    System.out.println("Enter details for Cheque #" + (i + 1) + ":");
                                    System.out.print("Account number: ");
                                    String acc = scanner.nextLine();
                                    System.out.print("Cheque number: ");
                                    String chq = scanner.nextLine();
                                    System.out.print("Currency: ");
                                    String curr = scanner.nextLine();
                                    System.out.print("Amount: ");
                                    double amt = scanner.nextDouble();
                                    scanner.nextLine();
                                    System.out.print("Signature: ");
                                    String sig = scanner.nextLine();
                                    batchCheques.add(new BatchCheque(acc, chq, curr, amt, sig));
                                }
                                adminService.createBatch(batchId, batchCheques);
                                break;
                            case 2:
                                adminService.displayBatches();
                                break;
                            case 3:
                                System.out.print("Enter Batch ID: ");
                                String viewBatchId = scanner.nextLine();
                                adminService.displayBatchDetails(viewBatchId);
                                break;
                            default:
                                break;
                        }
                        break;

                    case 15:
                        System.out.println("\n--- Admin: Reset Stuck Transactions ---");
                        System.out.println("1. Mark Cheque as Stuck");
                        System.out.println("2. Reset Stuck Cheque");
                        System.out.println("3. View Stuck Transactions");
                        System.out.println("4. Return");
                        System.out.print("Enter your choice: ");
                        int stuckChoice = scanner.nextInt();
                        scanner.nextLine();
                        switch (stuckChoice) {
                            case 1:
                                System.out.print("Enter Cheque Number to mark as stuck: ");
                                String stuckChq = scanner.nextLine();
                                adminService.markTransactionStuck(stuckChq);
                                break;
                            case 2:
                                System.out.print("Enter Cheque Number to reset: ");
                                String resetChq = scanner.nextLine();
                                adminService.resetStuckTransaction(resetChq);
                                break;
                            case 3:
                                adminService.displayStuckTransactions();
                                break;
                            default:
                                break;
                        }
                        break;
    
                    default:  
                        System.out.println("Invalid choice. Please try again.");  
                }
            }
        } catch (Exception ex) {
            Logger.error("Fatal error in main: " + ex.getMessage());
            ex.printStackTrace();
        }
    }

    /**
     * Handles the user login process.
     * @param scanner The scanner for user input
     * @param userService The user service for authentication
     * @return The authenticated User object, or null if login fails after retries
     */
    private static User performLogin(Scanner scanner, UserService userService) {
        final int MAX_ATTEMPTS = 3;
        for (int attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
            try {
                System.out.println("\n--- Login ---");
                System.out.print("Enter username: ");
                String username = scanner.nextLine();
                System.out.print("Enter password: ");
                String password = scanner.nextLine(); // In a real app, use a secure way to read password

                User user = userService.authenticate(username, password);
                if (user != null) {
                    Logger.info("User logged in: " + username);
                    System.out.println("Welcome, " + user.getUsername() + " (" + user.getRole() + ")!");
                    return user; // Login successful
                } else {
                    Logger.warn("Failed login attempt for user: " + username);
                    System.out.println("Invalid username or password. Attempt " + attempt + " of " + MAX_ATTEMPTS);
                }
            } catch (Exception ex) {
                Logger.error("Error during login: " + ex.getMessage());
            }
        }
        return null; // Login failed after max attempts
    }

    /**
     * Handles processing multiple cheques in a batch.
     * Prompts the user for the number of cheques and their details.
     * @param scanner The scanner for user input
     * @param chequeProcessor The cheque processor service
     */
    private static void processChequeBatch(Scanner scanner, ChequeProcessor chequeProcessor) {
        try {
            System.out.println("\n--- Batch Cheque Processing ---");
            System.out.print("Enter the number of cheques in the batch: ");
            int batchSize = scanner.nextInt();
            scanner.nextLine(); // Consume newline

            List<BatchCheque> chequesToProcess = new ArrayList<>();

            for (int i = 0; i < batchSize; i++) {
                try {
                    System.out.println("\nEnter details for Cheque #" + (i + 1) + ":");
                    System.out.print("Account number: ");
                    String accountNumber = scanner.nextLine();
                    System.out.print("Cheque number: ");
                    String chequeNumber = scanner.nextLine();
                    System.out.print("Currency (e.g., USD, EUR, GBP): ");
                    String currency = scanner.nextLine();
                    System.out.print("Amount: ");
                    double amount = scanner.nextDouble();
                    scanner.nextLine(); // Consume newline
                    System.out.print("Signature: ");
                    String signature = scanner.nextLine();

                    chequesToProcess.add(new BatchCheque(accountNumber, chequeNumber, currency, amount, signature));
                } catch (Exception ex) {
                    Logger.error("Error collecting cheque batch input: " + ex.getMessage());
                    scanner.nextLine(); // Clear buffer
                }
            }

            System.out.println("\nProcessing batch...");
            chequesToProcess.forEach(cheque -> {
                try {
                    chequeProcessor.processCheque(cheque.accountNumber, cheque.chequeNumber, cheque.currency, cheque.amount, cheque.signature);
                } catch (Exception ex) {
                    Logger.error("Error processing cheque in batch: " + ex.getMessage());
                }
            });
        } catch (Exception ex) {
            Logger.error("Batch processing error: " + ex.getMessage());
        }
    }
    
    /**
     * Display the currency exchange menu and handle user interactions
     * @param scanner The scanner for user input
     * @param currencyExchangeService The currency exchange service
     */
    private static void displayCurrencyExchangeMenu(Scanner scanner, CurrencyExchangeService currencyExchangeService) {
        while (true) {
            System.out.println("\n--- Currency Exchange Menu ---");
            System.out.println("1. View Supported Currencies");
            System.out.println("2. Get Exchange Rate");
            System.out.println("3. Get Detailed Exchange Rate Information");
            System.out.println("4. Convert Currency");
            System.out.println("5. Return to Main Menu");
            System.out.print("Enter your choice: ");
            
            int choice = scanner.nextInt();
            scanner.nextLine(); // Consume newline
            
            switch (choice) {
                case 1:
                    // Display supported currencies
                    List<String> supportedCurrencies = currencyExchangeService.getSupportedCurrencies();
                    System.out.println("\nSupported Currencies:");
                    for (String currencyCode : supportedCurrencies) {
                        System.out.println("- " + currencyCode);
                    }
                    break;
                    
                case 2:
                    // Get exchange rate
                    System.out.print("Enter currency code: ");
                    String currencyCode = scanner.nextLine().toUpperCase();
                    double rate = currencyExchangeService.getExchangeRate(currencyCode);
                    
                    if (rate > 0) {
                        System.out.println("Exchange rate for " + currencyCode + ": " + rate);
                    } else {
                        System.out.println("Currency not supported or exchange rate unavailable.");
                    }
                    break;
                    
                case 3:
                    // Get detailed exchange rate information
                    System.out.print("Enter currency code: ");
                    String detailCurrencyCode = scanner.nextLine().toUpperCase();
                    Map<String, Double> detailedRates = currencyExchangeService.getDetailedExchangeRates(detailCurrencyCode);
                    
                    if (!detailedRates.isEmpty()) {
                        System.out.println("\nDetailed Exchange Rate Information for " + detailCurrencyCode + ":");
                        System.out.println("Mid Rate: " + detailedRates.get("mid"));
                        System.out.println("Buy Rate: " + detailedRates.get("buy"));
                        System.out.println("Sell Rate: " + detailedRates.get("sell"));
                        System.out.println("Fee Rate: " + detailedRates.get("fee"));
                    } else {
                        System.out.println("Currency not supported or exchange rate unavailable.");
                    }
                    break;
                    
                case 4:
                    // Convert currency
                    System.out.print("Enter amount: ");
                    double amount = scanner.nextDouble();
                    scanner.nextLine(); // Consume newline
                    
                    System.out.print("Enter source currency code: ");
                    String fromCurrency = scanner.nextLine().toUpperCase();
                    
                    System.out.print("Enter target currency code: ");
                    String toCurrency = scanner.nextLine().toUpperCase();
                    
                    double convertedAmount = currencyExchangeService.convertCurrency(amount, fromCurrency, toCurrency);
                    
                    if (convertedAmount > 0) {
                        System.out.printf("%.2f %s = %.2f %s\n", amount, fromCurrency, convertedAmount, toCurrency);
                    } else {
                        System.out.println("Currency conversion failed. Please check the currency codes.");
                    }
                    break;
                    
                case 5:
                    // Return to main menu
                    return;
                    
                default:
                    System.out.println("Invalid choice. Please try again.");
            }
        }
    }

    /**
     * Handles the report generation menu and logic.
     * @param scanner The scanner for user input
     * @param chequeHistoryManager The cheque history manager
     */
    private static void handleReportGeneration(Scanner scanner, ChequeHistoryManager chequeHistoryManager) {
        System.out.println("\n--- Generate Cheque Reports ---");
        System.out.println("1. Daily Report (Today)");
        System.out.println("2. Weekly Report (Last 7 Days)");
        System.out.println("3. Monthly Report (Last 30 Days)");
        System.out.println("4. Custom Date Range Report");
        System.out.println("5. Return to Main Menu");
        System.out.print("Enter your choice: ");
        int choice = scanner.nextInt();
        scanner.nextLine(); // Consume newline

        LocalDate endDate = LocalDate.now();
        LocalDate startDate;
        String reportNamePrefix;

        switch (choice) {
            case 1: // Daily
                startDate = endDate;
                reportNamePrefix = "daily_report_";
                break;
            case 2: // Weekly
                startDate = endDate.minusDays(6); // Last 7 days including today
                reportNamePrefix = "weekly_report_";
                break;
            case 3: // Monthly
                startDate = endDate.minusDays(29); // Last 30 days including today
                reportNamePrefix = "monthly_report_";
                break;
            case 4: // Custom
                System.out.print("Enter start date (YYYY-MM-DD): ");
                String startDateStr = scanner.nextLine();
                System.out.print("Enter end date (YYYY-MM-DD): ");
                String endDateStr = scanner.nextLine();
                try {
                    startDate = LocalDate.parse(startDateStr, DateTimeFormatter.ISO_LOCAL_DATE);
                    endDate = LocalDate.parse(endDateStr, DateTimeFormatter.ISO_LOCAL_DATE);
                } catch (Exception e) {
                    System.out.println("Invalid date format. Please use YYYY-MM-DD.");
                    return;
                }
                if (startDate.isAfter(endDate)) {
                    System.out.println("Start date cannot be after end date.");
                    return;
                }
                reportNamePrefix = "custom_report_";
                break;
            case 5:
                return; // Return to main menu
            default:
                System.out.println("Invalid choice. Please try again.");
                return;
        }

        List<ChequeHistoryManager.ChequeRecord> records = chequeHistoryManager.getAllChequeRecordsInPeriod(startDate, endDate);

        if (records.isEmpty()) {
            System.out.println("No cheque records found for the selected period.");
            return;
        }

        String csvData = chequeHistoryManager.generateChequeReportCSV(records);
        String fileName = reportNamePrefix + startDate.format(DateTimeFormatter.ISO_LOCAL_DATE) +
                          "_to_" + endDate.format(DateTimeFormatter.ISO_LOCAL_DATE) + ".csv";

        try (BufferedWriter writer = new BufferedWriter(new FileWriter(fileName))) {
            writer.write(csvData);
            System.out.println("Report generated successfully: " + fileName);
        } catch (IOException e) {
            System.err.println("Error writing report to file: " + e.getMessage());
        }
    }

    /**
     * Handles the cheque printing simulation.
     * @param scanner The scanner for user input
     * @param printingService The cheque printing service
     */
    private static void handleChequePrinting(Scanner scanner, ChequePrintingService printingService) {
        System.out.println("\n--- Simulate Cheque Printing ---");

        System.out.print("Enter Payee Name: ");
        String payeeName = scanner.nextLine();

        System.out.print("Enter Amount: ");
        double amount = scanner.nextDouble();
        scanner.nextLine(); // Consume newline

        System.out.print("Enter Date (YYYY-MM-DD): ");
        String dateStr = scanner.nextLine();
        Date chequeDate;
        try {
            chequeDate = new SimpleDateFormat("yyyy-MM-dd").parse(dateStr);
        } catch (java.text.ParseException e) {
            System.out.println("Invalid date format. Please use YYYY-MM-DD. Using current date.");
            chequeDate = new Date();
        }

        System.out.print("Enter Account Number: ");
        String accountNumber = scanner.nextLine();

        System.out.print("Enter Cheque Number: ");
        String chequeNumber = scanner.nextLine();

        // You can make bankName configurable or a constant
        String bankName = "Global Trust Bank";

        printingService.printCheque(payeeName, amount, chequeDate, accountNumber, chequeNumber, bankName);
    }

    /**
     * Handles the process of "scanning", encrypting, signing, and "sending" a cheque image.
     * @param scanner Input scanner
     * @param imageHandler Service to handle image "upload"
     * @param cryptoService Service for encryption and signing
     * @param clearinghouseService Service to "send" to clearinghouse
     * @param currentUser The currently logged-in user
     */
    private static void handleChequeImageSubmission(Scanner scanner,
                                                    ChequeImageHandler imageHandler,
                                                    CryptographyService cryptoService,
                                                    ClearinghouseService clearinghouseService,
                                                    User currentUser) {
        System.out.println("\n--- Cheque Image Submission ---");
        System.out.print("Enter Account Number for the cheque: ");
        String accountNumber = scanner.nextLine();
        System.out.print("Enter Cheque Number: ");
        String chequeNumber = scanner.nextLine();
        System.out.print("Enter path to cheque image file (e.g., /path/to/cheque.jpg): ");
        String imagePath = scanner.nextLine();

        // 1. Simulate scanning and uploading image
        byte[] imageData = imageHandler.loadImageData(imagePath);
        if (imageData == null) {
            System.out.println("Failed to load image data. Aborting submission.");
            return;
        }
        System.out.println("Cheque image \"uploaded\" successfully from: " + imagePath);

        // 2. Encrypt the image data
        // In a real system, key management would be crucial.
        String encryptionKey = "a-very-secure-encryption-key"; // Placeholder
        byte[] encryptedImageData = cryptoService.encryptData(imageData, encryptionKey);
        System.out.println("Image data encrypted.");

        // 3. Sign the encrypted image data
        String privateKey = currentUser.getUsername() + "-private-key"; // Placeholder
        String digitalSignature = cryptoService.signData(encryptedImageData, privateKey);
        System.out.println("Encrypted image data signed. Signature: " + digitalSignature.substring(0, 10) + "..."); // Show partial signature

        // 4. Send to clearinghouse
        clearinghouseService.submitToClearinghouse(accountNumber, chequeNumber, encryptedImageData, digitalSignature);
    }

    // --- Existing Inner Classes (User, UserService, BatchCheque) ---
    // ... (Keep existing inner classes as they are)
    static class EmailNotificationService {
    public void sendEmail(String to, String subject, String body) {
        // In a real system, integrate with JavaMail or an SMTP server.
        // For simulation, just print to console.
        System.out.println("\n--- EMAIL NOTIFICATION ---");
        System.out.println("To: " + to);
        System.out.println("Subject: " + subject);
        System.out.println("Body:\n" + body);
        System.out.println("--------------------------\n");
    }
        }
        
    /**
     * Service for simulating cheque printing.
     */
    static class ChequePrintingService {
        public void printCheque(String payeeName, double amount, Date date, String accountNumber, String chequeNumber, String bankName) {
            SimpleDateFormat dateFormat = new SimpleDateFormat("dd-MMM-yyyy");
            NumberFormat currencyFormatter = NumberFormat.getCurrencyInstance(Locale.US); // Assuming USD

            System.out.println("\n+----------------------------------------------------------------------+");
            System.out.printf("| %-50s Date: %-10s |\n", bankName.toUpperCase(), dateFormat.format(date));
            System.out.println("|                                                                      |");
            System.out.printf("| Pay To: %-30s Amount: %-15s |\n", payeeName, currencyFormatter.format(amount));
            // Amount in words is complex, for simulation, we can skip or put a placeholder
            System.out.printf("| Amount in Words: %-45s |\n", "*(Numeric Amount Above)*");
            System.out.println("|                                                                      |");
            System.out.println("|                                                                      |");
            System.out.printf("| Account No: %-25s Cheque No: %-15s |\n", accountNumber, chequeNumber);
            System.out.println("|                                                                      |");
            System.out.println("|                                                 Signature:           |");
            System.out.println("|                                                 -------------------- |");
            System.out.println("+----------------------------------------------------------------------+");
            System.out.println("Cheque simulation printed successfully.\n");
        }
    }
    /**
 * Represents a user of the system (employee or account holder).
 */
    static class User {
        private String username;
        private String password; // In a real app, this would be hashed
        private String role; // e.g., "EMPLOYEE", "ACCOUNT_HOLDER"

        public User(String username, String password, String role) {
            this.username = username;
            this.password = password;
            this.role = role;
        }

        public String getUsername() {
            return username;
        }

        public String getPassword() {
            return password;
        }

        public String getRole() {
            return role;
        }
    }

    /**
     * Service for managing users and handling authentication.
     */
    static class UserService {
        private Map<String, User> users = new HashMap<>();

        public UserService() {
            // Add some sample users for demonstration
            registerUser("employee1", "password123", "EMPLOYEE");
            registerUser("account1001", "chequeuser", "ACCOUNT_HOLDER");
            registerUser("account1002", "securepass", "ACCOUNT_HOLDER");
        }

        /**
         * Registers a new user.
         * @param username The username
         * @param password The password
         * @param role The user's role
         */
        public void registerUser(String username, String password, String role) {
            users.put(username, new User(username, password, role));
            System.out.println("User registered: " + username + " (" + role + ")");
        }

        /**
         * Authenticates a user based on username and password.
         * @param username The username
         * @param password The password
         * @return The authenticated User object if successful, null otherwise
         */
        public User authenticate(String username, String password) {
            User user = users.get(username);
            if (user != null && user.getPassword().equals(password)) {
                System.out.println("Authentication successful for user: " + username);
                return user;
            }
            System.out.println("Authentication failed for user: " + username);
            return null;
        }
    }

    /**
     * Represents a single cheque transaction for batch processing.
     */
    static class BatchCheque {
        String accountNumber;
        String chequeNumber;
        String currency;
        double amount;
        String signature;

        public BatchCheque(String accountNumber, String chequeNumber, String currency, double amount, String signature) {
            this.accountNumber = accountNumber;
            this.chequeNumber = chequeNumber;
            this.currency = currency;
            this.amount = amount;
            this.signature = signature;
        }
    }

    /**
     * Manages exception reports for cheques (bounced, duplicate, altered, delayed).
     * Now supports recording FIR/legal complaint details for bounced cheques.
     */
    static class ExceptionReportManager {
        static class ExceptionRecord {
            String accountNumber, chequeNumber, type, details;
            Date date;
            FIRDetails firDetails; // New: FIR/legal complaint details

            ExceptionRecord(String accountNumber, String chequeNumber, String type, String details, Date date) {
                this.accountNumber = accountNumber;
                this.chequeNumber = chequeNumber;
                this.type = type;
                this.details = details;
                this.date = date;
                this.firDetails = null;
            }
        }

    // New: FIR/legal complaint details class
        static class FIRDetails {
            String firNumber;
            String policeStation;
            Date firDate;
            String remarks;

            FIRDetails(String firNumber, String policeStation, Date firDate, String remarks) {
                this.firNumber = firNumber;
                this.policeStation = policeStation;
                this.firDate = firDate;
                this.remarks = remarks;
            }
        }

        private List<ExceptionRecord> exceptions = new ArrayList<>();

        public void reportException(String accountNumber, String chequeNumber, String type, String details) {
            exceptions.add(new ExceptionRecord(accountNumber, chequeNumber, type, details, new Date()));
            System.out.println("Exception reported: " + type + " for Cheque " + chequeNumber + " (" + details + ")");
        }

        // New: Record FIR/legal complaint details for a bounced cheque
        public boolean recordFIRDetails(String accountNumber, String chequeNumber, String firNumber, String policeStation, Date firDate, String remarks) {
            for (ExceptionRecord ex : exceptions) {
                if (ex.accountNumber.equals(accountNumber)
                        && ex.chequeNumber.equals(chequeNumber)
                        && "Bounced".equalsIgnoreCase(ex.type)) {
                    ex.firDetails = new FIRDetails(firNumber, policeStation, firDate, remarks);
                    System.out.println("FIR/legal complaint details recorded for bounced cheque " + chequeNumber);
                    return true;
                }
            }
            System.out.println("No bounced cheque exception found for the given account and cheque number.");
            return false;
        }

        public void displayExceptions() {
            if (exceptions.isEmpty()) {
                System.out.println("No cheque exceptions reported.");
                return;
            }
            System.out.println("\n--- Cheque Exception Report ---");
            for (ExceptionRecord ex : exceptions) {
                System.out.printf("Date: %s | Account: %s | Cheque: %s | Type: %s | Details: %s\n",
                    new SimpleDateFormat("yyyy-MM-dd HH:mm").format(ex.date),
                    ex.accountNumber, ex.chequeNumber, ex.type, ex.details);
                // Show FIR/legal complaint details if present
                if ("Bounced".equalsIgnoreCase(ex.type) && ex.firDetails != null) {
                    System.out.printf("   FIR No: %s | Police Station: %s | FIR Date: %s | Remarks: %s\n",
                        ex.firDetails.firNumber,
                        ex.firDetails.policeStation,
                        new SimpleDateFormat("yyyy-MM-dd").format(ex.firDetails.firDate),
                        ex.firDetails.remarks);
                }
            }
        }
    }

    /**
     * Enum to represent cheque status.
     */
    enum ChequeStatus {
        ISSUED,
        PROCESSED,
        CANCELED
    }

    /**
     * ChequeStatusManager to track the status of cheques.
     */
    static class ChequeStatusManager {
        // Key: accountNumber + ":" + chequeNumber, Value: ChequeStatus
        private Map<String, ChequeStatus> chequeStatusMap = new HashMap<>();

        public void setStatus(String accountNumber, String chequeNumber, ChequeStatus status) {
            chequeStatusMap.put(accountNumber + ":" + chequeNumber, status);
            System.out.println("Status of cheque " + chequeNumber + " for account " + accountNumber + " set to " + status);
        }

        public ChequeStatus getStatus(String accountNumber, String chequeNumber) {
            return chequeStatusMap.getOrDefault(accountNumber + ":" + chequeNumber, null);
        }

        public void displayAllStatuses() {
            if (chequeStatusMap.isEmpty()) {
                System.out.println("No cheque statuses recorded.");
                return;
            }
            System.out.println("\n--- Cheque Statuses ---");
            for (Map.Entry<String, ChequeStatus> entry : chequeStatusMap.entrySet()) {
                String[] parts = entry.getKey().split(":");
                System.out.printf("Account: %s | Cheque: %s | Status: %s\n", parts[0], parts[1], entry.getValue());
            }
        }
    }

    /**
     * Simple Logger utility for error/info/debug logging.
     */
    static class Logger {
        public enum Level { INFO, WARN, ERROR, DEBUG }

        public static void log(Level level, String message) {
            String timestamp = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss").format(new Date());
            System.out.printf("[%s] [%s] %s%n", timestamp, level, message);
        }

        public static void info(String message) { log(Level.INFO, message); }
        public static void warn(String message) { log(Level.WARN, message); }
        public static void error(String message) { log(Level.ERROR, message); }
        public static void debug(String message) { log(Level.DEBUG, message); }
        }

    /**
     * Simulates handling of cheque images.
     */
    static class ChequeImageHandler {
        /**
         * Simulates loading image data from a file path.
         * In a real application, this would involve actual file I/O and image processing.
         * @param filePath The path to the image file.
         * @return A byte array representing the image data, or null on failure.
         */
        public byte[] loadImageData(String filePath) {
            if (filePath == null || filePath.trim().isEmpty()) {
                System.out.println("Error: Image file path cannot be empty.");
                return null;
            }
            // Simulate reading file content. For this demo, we'll just use the path string as bytes.
            // In a real app: Files.readAllBytes(Paths.get(filePath));
            System.out.println("Simulating reading image from: " + filePath);
            return ("ImageData:" + filePath + ":Content").getBytes(StandardCharsets.UTF_8);
        }
    }

    /**
     * Simulates cryptographic operations like encryption and digital signing.
     */
    static class CryptographyService {
        /**
         * Simulates encrypting data.
         * @param data The data to encrypt.
         * @param key The encryption key.
         * @return Mock encrypted data.
         */
        public byte[] encryptData(byte[] data, String key) {
            // This is a placeholder. Real encryption would use JCA (Java Cryptography Architecture).
            // For simulation, let's just prepend "encrypted-" and append the key.
            String originalData = new String(data, StandardCharsets.UTF_8);
            String encryptedString = "encrypted(" + key + "):" + originalData;
            return encryptedString.getBytes(StandardCharsets.UTF_8);
        }

        /**
         * Simulates digitally signing data.
         * @param data The data to sign.
         * @param privateKey The private key for signing.
         * @return A mock digital signature.
         */
        public String signData(byte[] data, String privateKey) {
            // This is a placeholder. Real digital signatures use algorithms like RSA, ECDSA.
            // For simulation, create a simple hash-like string.
            int hashCode = Arrays.hashCode(data);
            return "signature(" + privateKey + "):" + Integer.toHexString(hashCode) + Long.toHexString(System.nanoTime());
        }
    }

    /**
     * Simulates sending data to a clearinghouse.
     */
    static class ClearinghouseService {
        /**
         * Simulates submitting cheque image data and signature to a clearinghouse.
         * @param accountNumber The account number.
         * @param chequeNumber The cheque number.
         * @param encryptedImageData The encrypted image data.
         * @param digitalSignature The digital signature.
         */
        public void submitToClearinghouse(String accountNumber, String chequeNumber, byte[] encryptedImageData, String digitalSignature) {
            System.out.println("\n--- Submitting to Clearinghouse ---");
            System.out.println("Account: " + accountNumber + ", Cheque: " + chequeNumber);
            System.out.println("Encrypted Data Length: " + encryptedImageData.length + " bytes");
            System.out.println("Digital Signature: " + digitalSignature.substring(0, Math.min(digitalSignature.length(), 20)) + "..."); // Show partial signature
            System.out.println("Simulating sending via SFTP/REST API...");
            System.out.println("Submission to clearinghouse successful (simulated).");
            System.out.println("---------------------------------");
        }
    }

    /**
     * Mock implementation of ChequeHistoryManager.
     */
    static class ChequeHistoryManager {
        static class ChequeRecord {
            String accountNumber, chequeNumber, currency;
            double amount;
            Date date;
            ChequeRecord(String acc, String chq, String curr, double amt, Date d) {
                this.accountNumber = acc; this.chequeNumber = chq; this.currency = curr; this.amount = amt; this.date = d;
            }
        }
        private Map<String, List<ChequeRecord>> history = new HashMap<>();
        public void recordCheque(String acc, String chq, String curr, double amt, Date d) {
            history.computeIfAbsent(acc, k -> new ArrayList<>()).add(new ChequeRecord(acc, chq, curr, amt, d));
        }
        public void displayChequeHistory(String acc) {
            System.out.println("History for " + acc + ": " + history.getOrDefault(acc, Collections.emptyList()).size() + " records.");
        }
        public List<String> getChequeNumbers(String acc) { return new ArrayList<>(); }
        public int getTotalChequeCount(String acc) { return 0; }
        public int getRecentChequeCount(String acc) { return 0; }
        public boolean hasSimilarRecentCheque(String acc, double amt, double threshold) { return false; }
        public List<ChequeRecord> getAllChequeRecordsInPeriod(LocalDate start, LocalDate end) { return new ArrayList<>(); }
        public String generateChequeReportCSV(List<ChequeRecord> records) { return "CSV Data"; }
    }

    /**
     * Mock implementation of CoreBankingSystemUpdater.
     */
    static class CoreBankingSystemUpdater {
        public void updateCoreBankingSystem(String acc, double amt) {
            System.out.println("Core Banking Updated for " + acc + " with amount " + amt);
        }
    }


    /**
     * Mock implementation of CoreBankingSystemUpdater.
     */
    static class CoreBankingSystemUpdater {
        public void updateCoreBankingSystem(String acc, double amt) {
            System.out.println("Core Banking Updated for " + acc + " with amount " + amt);
        }
    }


    /**
     * Service for verifying signatures on cheques.
     * This is a simplified implementation for demonstration purposes.
     */
    static class SignatureVerificationService {
        private Map<String, String> accountSignatures = new HashMap<>();

        public SignatureVerificationService() {
            // Initialize with some sample signatures for testing
            accountSignatures.put("1001", "John Doe");
            accountSignatures.put("1002", "Jane Smith");
            accountSignatures.put("1003", "Robert Johnson");
        }

        /**
         * Verifies if the provided signature matches the one on file for the account.
         *
         * @param accountNumber The account number
         * @param signature The signature to verify
         * @return true if the signature is valid, false otherwise
         */
        public boolean verifySignature(String accountNumber, String signature) {
            System.out.println("Verifying signature for account: " + accountNumber);

            // If we don't have a signature on file, accept any signature (for demo purposes)
            if (!accountSignatures.containsKey(accountNumber)) {
                System.out.println("No signature on file for account: " + accountNumber + ". Accepting new signature.");
                accountSignatures.put(accountNumber, signature);
                return true;
            }

            // Compare the provided signature with the one on file
            String storedSignature = accountSignatures.get(accountNumber);
            boolean isValid = storedSignature.equals(signature);

            if (isValid) {
                System.out.println("Signature verified successfully.");
            } else {
                System.out.println("Signature verification failed.");
            }

            return isValid;
        }

        /**
         * Updates the signature on file for an account.
         *
         * @param accountNumber The account number
         * @param newSignature The new signature
         */
        public void updateSignature(String accountNumber, String newSignature) {
            accountSignatures.put(accountNumber, newSignature);
            System.out.println("Signature updated for account: " + accountNumber);
        }
    }

    /**
     * Module for processing cheques with signature verification, fraud detection,
     * currency conversion, and core banking system update.
     */
    static class ChequeProcessor {
        private CurrencyExchangeService currencyExchangeService;
        private SignatureVerificationService signatureVerificationService;
        private CoreBankingSystemUpdater coreBankingSystemUpdater;
        private ChequeHistoryManager chequeHistoryManager;
        private FraudDetectionService fraudDetectionService;
        private ExceptionReportManager exceptionReportManager;
        private ChequeStatusManager chequeStatusManager;
        private EmailNotificationService emailNotificationService;

        public ChequeProcessor(CurrencyExchangeService currencyExchangeService,
                               SignatureVerificationService signatureVerificationService,
                               CoreBankingSystemUpdater coreBankingSystemUpdater,
                               ChequeHistoryManager chequeHistoryManager,
                               FraudDetectionService fraudDetectionService,
                               ExceptionReportManager exceptionReportManager,
                               ChequeStatusManager chequeStatusManager,
                               EmailNotificationService emailNotificationService) {
            this.currencyExchangeService = currencyExchangeService;
            this.signatureVerificationService = signatureVerificationService;
            this.coreBankingSystemUpdater = coreBankingSystemUpdater;
            this.chequeHistoryManager = chequeHistoryManager;
            this.fraudDetectionService = fraudDetectionService;
            this.exceptionReportManager = exceptionReportManager;
            this.chequeStatusManager = chequeStatusManager;
            this.emailNotificationService = emailNotificationService;
        }

        public void processCheque(String accountNumber, String chequeNumber, String currency, double amount, String signature) {
            try {
                // Mark as issued if not already tracked
                if (chequeStatusManager.getStatus(accountNumber, chequeNumber) == null) {
                    chequeStatusManager.setStatus(accountNumber, chequeNumber, ChequeStatus.ISSUED);
                }

                Logger.info("Processing cheque: " + chequeNumber + " for account: " + accountNumber);

                System.out.println("Processing cheque...");

                // Step 1: Verify signature
                if (!signatureVerificationService.verifySignature(accountNumber, signature)) {
                    exceptionReportManager.reportException(accountNumber, chequeNumber, "Altered", "Signature mismatch");
                    Logger.warn("Signature verification failed for cheque: " + chequeNumber);
                    System.out.println("Signature verification failed. Cheque processing aborted.");
                    // Send email notification
                    emailNotificationService.sendEmail(
                        accountNumber + "@bank.com",
                        "Cheque Validation Failure",
                        "Cheque " + chequeNumber + " for account " + accountNumber + " failed signature verification."
                    );
                    return;
                }

                // Step 2: Fraud detection
                if (fraudDetectionService.isFraudulentCheque(accountNumber, chequeNumber, amount)) {
                    exceptionReportManager.reportException(accountNumber, chequeNumber, "Duplicate", "Fraudulent or duplicate cheque detected");
                    Logger.warn("Fraudulent cheque detected: " + chequeNumber);
                    System.out.println("Fraudulent cheque detected. Cheque processing aborted.");
                    // Send email notification
                    emailNotificationService.sendEmail(
                        accountNumber + "@bank.com",
                        "Fraud Detection Alert",
                        "Potential fraud detected for cheque " + chequeNumber + " on account " + accountNumber + "."
                    );
                    return;
                }

                // Simulate bounced cheque (for demo, if amount > 50000)
                if (amount > 50000) {
                    exceptionReportManager.reportException(accountNumber, chequeNumber, "Bounced", "Insufficient funds (simulated)");
                    Logger.warn("Cheque bounced due to high amount: " + chequeNumber);
                    System.out.println("Cheque bounced due to insufficient funds. Cheque processing aborted.");
                    // Send email notification
                    emailNotificationService.sendEmail(
                        accountNumber + "@bank.com",
                        "Cheque Bounced Notification",
                        "Cheque " + chequeNumber + " for account " + accountNumber + " has bounced due to insufficient funds."
                    );
                    return;
                }

                // Simulate delayed cheque (for demo, if cheque number ends with '9')
                if (chequeNumber.endsWith("9")) {
                    exceptionReportManager.reportException(accountNumber, chequeNumber, "Delayed", "Cheque processing delayed (simulated)");
                    Logger.info("Cheque processing delayed for cheque: " + chequeNumber);
                    System.out.println("Cheque processing delayed (simulated).");
                    // Optional: send notification for delayed cheques if desired
                }

                // Step 3: Get detailed exchange rate information if currency is not local
                double amountInLocalCurrency = amount;
                if (!"USD".equalsIgnoreCase(currency)) { // USD is the base currency
                    Map<String, Double> detailedRates = currencyExchangeService.getDetailedExchangeRates(currency);

                    if (detailedRates.isEmpty()) {
                        Logger.error("Exchange rate unavailable for currency: " + currency);
                        System.out.println("Failed to fetch exchange rate. Cheque processing aborted.");
                        return;
                    }

                    // Use the buy rate for incoming transactions
                    double buyRate = detailedRates.get("buy");
                    double fee = detailedRates.get("fee");

                    // Step 4: Convert amount to local currency with detailed calculations
                    amountInLocalCurrency = amount * buyRate;
                    double feeAmount = amount * fee;

                    System.out.println("Currency: " + currency.toUpperCase());
                    System.out.println("Original amount: " + amount);
                    System.out.println("Exchange rate (buy): " + buyRate);
                    System.out.println("Fee rate: " + fee);
                    System.out.println("Fee amount: " + feeAmount);
                    System.out.println("Amount in local currency (before fees): " + amountInLocalCurrency);

                    // Apply fee
                    amountInLocalCurrency -= feeAmount;
                    System.out.println("Final amount in local currency (USD): " + amountInLocalCurrency);
                } else {
                    System.out.println("Processing in local currency (USD): " + amountInLocalCurrency);
                }

                // Step 5: Update core banking system
                coreBankingSystemUpdater.updateCoreBankingSystem(accountNumber, amountInLocalCurrency);

                // Step 6: Record cheque history
                chequeHistoryManager.recordCheque(accountNumber, chequeNumber, currency, amount, new java.util.Date());

                // If cheque is processed successfully:
                chequeStatusManager.setStatus(accountNumber, chequeNumber, ChequeStatus.PROCESSED);
                Logger.info("Cheque processed successfully: " + chequeNumber);
                System.out.println("Cheque processed successfully.");
            } catch (Exception ex) {
                Logger.error("Error processing cheque " + chequeNumber + ": " + ex.getMessage());
                exceptionReportManager.reportException(accountNumber, chequeNumber, "ProcessingError", ex.getMessage());
                System.out.println("An error occurred during cheque processing. Please check logs.");
                // Send email notification for processing error
                emailNotificationService.sendEmail(
                    accountNumber + "@bank.com",
                    "Cheque Processing Error",
                    "An error occurred while processing cheque " + chequeNumber + " for account " + accountNumber + ": " + ex.getMessage()
                );
            }
        }

        // Add a method to cancel a cheque
        public void cancelCheque(String accountNumber, String chequeNumber) {
            try {
                chequeStatusManager.setStatus(accountNumber, chequeNumber, ChequeStatus.CANCELED);
                Logger.info("Cheque canceled: " + chequeNumber + " for account: " + accountNumber);
                System.out.println("Cheque " + chequeNumber + " for account " + accountNumber + " has been canceled.");
            } catch (Exception ex) {
                Logger.error("Error canceling cheque " + chequeNumber + ": " + ex.getMessage());
                System.out.println("An error occurred while canceling the cheque.");
            }
        }
    }

    /**
     * Enhanced Currency Exchange Service
     * Supports multiple currencies with detailed exchange rate calculations
     * and dynamic fetching of rates from external sources.
     */
    static class CurrencyExchangeService {
        private Map<String, CurrencyRate> exchangeRateCache = new HashMap<>();
        private static final String BASE_CURRENCY = "USD";
        private static final long CACHE_EXPIRY_MINUTES = 60; // Cache expiry time in minutes
        private static final String API_KEY = "demo"; // Replace with your actual API key for production

        // Fallback exchange rates in case API is unavailable
        private static final Map<String, Double> FALLBACK_RATES = new HashMap<String, Double>() {{
            put("EUR", 1.1);
            put("GBP", 1.3);
            put("INR", 0.013);
            put("JPY", 0.0091);
            put("CAD", 0.74);
            put("AUD", 0.67);
            put("CHF", 1.12);
            put("CNY", 0.14);
            put("HKD", 0.13);
            put("NZD", 0.62);
        }};

        /**
         * Get the exchange rate for a specific currency
         * @param currency The currency code (e.g., EUR, GBP)
         * @return The exchange rate relative to the base currency (USD)
         */
        public double getExchangeRate(String currency) {
            System.out.println("Fetching exchange rate for currency: " + currency);

            // Standardize currency code
            String currencyCode = currency.toUpperCase();

            // Return 1.0 if it's the base currency
            if (BASE_CURRENCY.equals(currencyCode)) {
                return 1.0;
            }

            // Check cache first
            if (isCacheValid(currencyCode)) {
                CurrencyRate cachedRate = exchangeRateCache.get(currencyCode);
                System.out.println("Using cached rate: " + cachedRate.getRate() + " (Last updated: " +
                        cachedRate.getLastUpdated().format(java.time.format.DateTimeFormatter.ISO_LOCAL_DATE_TIME) + ")");
                return cachedRate.getRate();
            }

            // Try to fetch from external API
            try {
                double apiRate = fetchRateFromAPI(currencyCode);
                if (apiRate > 0) {
                    // Cache the new rate
                    exchangeRateCache.put(currencyCode, new CurrencyRate(apiRate, java.time.LocalDateTime.now()));
                    return apiRate;
                }
            } catch (Exception e) {
                System.out.println("Error fetching exchange rate from API: " + e.getMessage());
                // Continue to fallback rates
            }

            // Use fallback rates if API fetch failed
            Double fallbackRate = FALLBACK_RATES.get(currencyCode);
            if (fallbackRate != null) {
                System.out.println("Using fallback rate for " + currencyCode + ": " + fallbackRate);
                // Cache the fallback rate
                exchangeRateCache.put(currencyCode, new CurrencyRate(fallbackRate, java.time.LocalDateTime.now()));
                return fallbackRate;
            }

            System.out.println("No exchange rate available for currency: " + currencyCode);
            return 0.0;
        }

        /**
         * Convert an amount from one currency to another
         * @param amount The amount to convert
         * @param fromCurrency The source currency
         * @param toCurrency The target currency
         * @return The converted amount
         */
        public double convertCurrency(double amount, String fromCurrency, String toCurrency) {
            double fromRate = getExchangeRate(fromCurrency);
            double toRate = getExchangeRate(toCurrency);

            if (fromRate <= 0 || toRate <= 0) {
                System.out.println("Cannot convert: invalid exchange rates");
                return 0.0;
            }

            // Convert to base currency first, then to target currency
            double amountInBaseCurrency = amount * fromRate;
            double convertedAmount = amountInBaseCurrency / toRate;

            System.out.println(String.format("Converted %.2f %s to %.2f %s",
                    amount, fromCurrency.toUpperCase(), convertedAmount, toCurrency.toUpperCase()));

            return convertedAmount;
        }

        /**
         * Get detailed exchange rate information including buy/sell rates and fees
         * @param currency The currency code
         * @return A map containing detailed rate information
         */
        public Map<String, Double> getDetailedExchangeRates(String currency) {
            String currencyCode = currency.toUpperCase();
            double baseRate = getExchangeRate(currencyCode);

            if (baseRate <= 0) {
                return Collections.emptyMap();
            }

            Map<String, Double> detailedRates = new HashMap<>();
            detailedRates.put("mid", baseRate);

            // Calculate buy rate (slightly lower than mid rate)
            double buyRate = baseRate * 0.99;
            detailedRates.put("buy", buyRate);

            // Calculate sell rate (slightly higher than mid rate)
            double sellRate = baseRate * 1.01;
            detailedRates.put("sell", sellRate);

            // Calculate fees
            double fee = baseRate * 0.005; // 0.5% fee
            detailedRates.put("fee", fee);

            return detailedRates;
        }

        /**
         * Get a list of all supported currencies
         * @return A list of supported currency codes
         */
        public List<String> getSupportedCurrencies() {
            List<String> currencies = new ArrayList<>();
            currencies.add(BASE_CURRENCY);
            currencies.addAll(FALLBACK_RATES.keySet());

            // Sort alphabetically
            Collections.sort(currencies);
            return currencies;
        }

        /**
         * Check if the cached rate is still valid
         * @param currency The currency code
         * @return true if the cache is valid, false otherwise
         */
        private boolean isCacheValid(String currency) {
            if (!exchangeRateCache.containsKey(currency)) {
                return false;
            }

            CurrencyRate cachedRate = exchangeRateCache.get(currency);
            java.time.LocalDateTime now = java.time.LocalDateTime.now();
            java.time.LocalDateTime expiryTime = cachedRate.getLastUpdated().plusMinutes(CACHE_EXPIRY_MINUTES);

            return now.isBefore(expiryTime);
        }

        /**
         * Fetch exchange rate from an external API
         * @param currency The currency code
         * @return The exchange rate
         * @throws Exception If there's an error fetching the rate
         */
        private double fetchRateFromAPI(String currency) throws Exception {
            // Using Open Exchange Rates API as an example
            // In a real application, you would use a proper API key
            String apiUrl = "https://open.er-api.com/v6/latest/" + BASE_CURRENCY + "?apikey=" + API_KEY;

            try {
                java.net.URL url = new java.net.URL(apiUrl);
                connection.setReadTimeout(5000);

                int status = connection.getResponseCode();
                if (status != 200) {
                    throw new Exception("API returned status code: " + status);
                }

                java.io.BufferedReader reader = new java.io.BufferedReader(new java.io.InputStreamReader(connection.getInputStream()));
                StringBuilder response = new StringBuilder();
                String line;
                while ((line = reader.readLine()) != null) {
                    response.append(line);
                }
                reader.close();

                // Parse JSON response
                org.json.simple.parser.JSONParser parser = new org.json.simple.parser.JSONParser();
                org.json.simple.JSONObject jsonObject = (org.json.simple.JSONObject) parser.parse(response.toString());
                org.json.simple.JSONObject rates = (org.json.simple.JSONObject) jsonObject.get("rates");

                if (rates != null && rates.containsKey(currency)) {
                    double rate = ((Number) rates.get(currency)).doubleValue();
                    System.out.println("Fetched rate from API for " + currency + ": " + rate);
                    return rate;
                } else {
                    throw new Exception("Currency not found in API response");
                }
            } catch (Exception e) {
                System.out.println("API fetch failed: " + e.getMessage());
                throw e;
            }
        }

        /**
         * Clear the exchange rate cache
         */
        public void clearCache() {
            exchangeRateCache.clear();
            System.out.println("Exchange rate cache cleared");
        }
    }

        /**
     * Enhanced Currency Exchange Service V1
     * Supports multiple currencies with detailed exchange rate calculations
     * and dynamic fetching of rates from external sources.
     */
    // Inefficient and non-best-practice version of CurrencyExchangeServiceV2
    static class CurrencyExchangeServiceV2 {
        private Map<String, Double> cache = new HashMap<>();
        private static final String BASE = "USD";
        private static final String KEY = "demo";
        // Fallback rates
        private static final Map<String, Double> RATES = new HashMap<String, Double>();
        static {
            RATES.put("EUR", 1.1);
            RATES.put("GBP", 1.3);
            RATES.put("INR", 0.013);
            RATES.put("JPY", 0.0091);
            RATES.put("CAD", 0.74);
            RATES.put("AUD", 0.67);
            RATES.put("CHF", 1.12);
            RATES.put("CNY", 0.14);
            RATES.put("HKD", 0.13);
            RATES.put("NZD", 0.62);
        }

        public double getExchangeRateV2(String currency) {
            String c = currency;
            if (c == null) return 0.0;
            c = c.toUpperCase();
            if (c.equals(BASE)) return 1.0;
            if (cache.containsKey(c)) return cache.get(c);
            double rate = 0.0;
            try {
                rate = fetchRateFromAPIV2(c);
                cache.put(c, rate);
                return rate;
            } catch (Exception e) {
                // ignore
            }
            if (RATES.containsKey(c)) {
                cache.put(c, RATES.get(c));
                return RATES.get(c);
            }
            return 0.0;
        }

        public double convertCurrencyV2(double amount, String from, String to) {
            double r1 = getExchangeRateV2(from);
            double r2 = getExchangeRateV2(to);
            if (r1 == 0.0 || r2 == 0.0) return 0.0;
            return (amount * r1) / r2;
        }

        public Map<String, Double> getDetailedExchangeRatesV2(String currency) {
            Map<String, Double> m = new HashMap<>();
            double r = getExchangeRateV2(currency);
            if (r == 0.0) return m;
            m.put("mid", r);
            m.put("buy", r - 0.01 * r);
            m.put("sell", r + 0.01 * r);
            m.put("fee", r * 0.005);
            return m;
        }

        public List<String> getSupportedCurrenciesV2() {
            List<String> l = new ArrayList<>();
            l.add(BASE);
            for (String k : RATES.keySet()) l.add(k);
            return l;
        }

        private double fetchRateFromAPIV2(String currency) throws Exception {
            String url = "https://open.er-api.com/v6/latest/" + BASE + "?apikey=" + KEY;
            java.net.URL u = new java.net.URL(url);
            java.net.HttpURLConnection c = (java.net.HttpURLConnection) u.openConnection();
            c.setRequestMethod("GET");
            int s = c.getResponseCode();
            if (s != 200) throw new Exception("bad");
            java.io.BufferedReader r = new java.io.BufferedReader(new java.io.InputStreamReader(c.getInputStream()));
            String line, all = "";
            while ((line = r.readLine()) != null) all += line;
            r.close();
            // Very inefficient JSON parsing
            int idx = all.indexOf("\"" + currency + "\":");
            if (idx == -1) throw new Exception("not found");
            int start = idx + currency.length() + 3;
            int end = start;
            while (end < all.length() && (Character.isDigit(all.charAt(end)) || all.charAt(end)=='.')) end++;
            String num = all.substring(start, end);
            return Double.parseDouble(num);
        }

        public void clearCacheV2() {
            cache.clear();
        }
    }

    /**
     * Class to store currency rate information with timestamp
     */
    static class CurrencyRate {
        private double rate;
        private java.time.LocalDateTime lastUpdated;

        public CurrencyRate(double rate, java.time.LocalDateTime lastUpdated) {
            this.rate = rate;
            this.lastUpdated = lastUpdated;
        }

        public double getRate() {
            return rate;
        }

        public java.time.LocalDateTime getLastUpdated() {
            return lastUpdated;
        }
    }

    /**
     * Service for detecting fraudulent cheque activities.
     * Implements various fraud detection mechanisms and uses ChequeHistoryManager.
     */
    static class FraudDetectionService {
        private FraudDetection fraudDetection;
        private ChequeHistoryManager historyManager;
        private Map<String, List<ChequeTransaction>> recentTransactions;

        // Fraud detection thresholds
        private static final int VELOCITY_CHECK_DAYS = 7;
        private static final int VELOCITY_THRESHOLD = 5;
        private static final double PATTERN_THRESHOLD = 0.95; // 95% similarity threshold
        private static final double SIMILAR_AMOUNT_THRESHOLD = 0.90; // 90% similarity threshold
        private static final int UNUSUAL_FREQUENCY_THRESHOLD = 3; // 3x normal frequency

        // Fraud alert levels
        public enum AlertLevel {
            LOW,
            MEDIUM,
            HIGH,
            CRITICAL
        }

        public FraudDetectionService() {
            this.fraudDetection = new FraudDetection();
            this.recentTransactions = new HashMap<>();
        }

        public void setHistoryManager(ChequeHistoryManager historyManager) {
            this.historyManager = historyManager;
        }

        public boolean isFraudulentCheque(String accountId, String chequeNumber, double amount) {
            boolean isDuplicate = checkDuplicateCheque(accountId, chequeNumber);
            boolean isAbnormal = checkAbnormalAmount(amount);
            boolean isSuspicious = checkSuspiciousActivity(accountId, amount);
            boolean isVelocityFraud = checkVelocityFraud(accountId, amount);
            boolean isPatternFraud = checkPatternFraud(accountId, amount);

            boolean isHistoricalDuplicate = false;
            boolean isUnusualFrequency = false;
            boolean isSimilarToRecent = false;

            if (historyManager != null) {
                isHistoricalDuplicate = checkHistoricalDuplicate(accountId, chequeNumber);
                isUnusualFrequency = checkUnusualFrequency(accountId);
                isSimilarToRecent = checkSimilarToRecent(accountId, amount);
            }

            logFraudChecks(accountId, chequeNumber, amount, isDuplicate, isAbnormal,
                    isSuspicious, isVelocityFraud, isPatternFraud,
                    isHistoricalDuplicate, isUnusualFrequency, isSimilarToRecent);

            AlertLevel alertLevel = determineAlertLevel(isDuplicate, isAbnormal,
                    isSuspicious, isVelocityFraud, isPatternFraud,
                    isHistoricalDuplicate, isUnusualFrequency, isSimilarToRecent);

            System.out.println("Fraud Alert Level: " + alertLevel);

            return isDuplicate || isAbnormal || isSuspicious || isVelocityFraud || isPatternFraud ||
                    isHistoricalDuplicate || isUnusualFrequency || isSimilarToRecent;
        }

        private boolean checkDuplicateCheque(String accountId, String chequeNumber) {
            return fraudDetection.isDuplicateCheque(accountId, chequeNumber);
        }

        private boolean checkAbnormalAmount(double amount) {
            return fraudDetection.isAbnormalAmount(amount);
        }

        private boolean checkSuspiciousActivity(String accountId, double amount) {
            return fraudDetection.isSuspiciousActivity(accountId, amount);
        }

        private boolean checkVelocityFraud(String accountId, double amount) {
            if (!recentTransactions.containsKey(accountId)) {
                recentTransactions.put(accountId, new ArrayList<>());
            }
            ChequeTransaction currentTransaction = new ChequeTransaction(amount, java.time.LocalDate.now());
            List<ChequeTransaction> transactions = recentTransactions.get(accountId);
            transactions.add(currentTransaction);

            java.time.LocalDate cutoffDate = java.time.LocalDate.now().minusDays(VELOCITY_CHECK_DAYS);
            long recentCount = transactions.stream()
                    .filter(t -> !t.getDate().isBefore(cutoffDate))
                    .count();

            // Clean up old transactions
            recentTransactions.put(accountId, transactions.stream()
                    .filter(t -> !t.getDate().isBefore(cutoffDate))
                    .toList());

            return recentCount > VELOCITY_THRESHOLD;
        }

        private boolean checkPatternFraud(String accountId, double amount) {
            if (!recentTransactions.containsKey(accountId)) {
                return false;
            }
            List<ChequeTransaction> transactions = recentTransactions.get(accountId);
            if (transactions.size() < 3) {
                return false;
            }
            List<Double> amounts = transactions.stream()
                    .map(ChequeTransaction::getAmount)
                    .toList();
            double similarCount = 0;
            for (Double pastAmount : amounts) {
                double similarity = 1.0 - Math.abs(pastAmount - amount) / Math.max(pastAmount, amount);
                if (similarity > PATTERN_THRESHOLD) {
                    similarCount++;
                }
            }
            return similarCount >= 3;
        }

        private boolean checkHistoricalDuplicate(String accountId, String chequeNumber) {
            List<String> historicalCheques = historyManager.getChequeNumbers(accountId);
            return historicalCheques.contains(chequeNumber);
        }

        private boolean checkUnusualFrequency(String accountId) {
            int totalCheques = historyManager.getTotalChequeCount(accountId);
            int recentCheques = historyManager.getRecentChequeCount(accountId);
            if (totalCheques < 10) {
                return false;
            }
            double avgMonthlyFrequency = totalCheques / 3.0;
            return recentCheques > avgMonthlyFrequency * UNUSUAL_FREQUENCY_THRESHOLD;
        }

        private boolean checkSimilarToRecent(String accountId, double amount) {
            return historyManager.hasSimilarRecentCheque(accountId, amount, SIMILAR_AMOUNT_THRESHOLD);
        }

        private AlertLevel determineAlertLevel(boolean isDuplicate, boolean isAbnormal,
                                               boolean isSuspicious, boolean isVelocityFraud,
                                               boolean isPatternFraud, boolean isHistoricalDuplicate,
                                               boolean isUnusualFrequency, boolean isSimilarToRecent) {
            int fraudCount = 0;
            if (isDuplicate || isHistoricalDuplicate) fraudCount += 3;
            if (isAbnormal) fraudCount += 2;
            if (isSuspicious) fraudCount += 2;
            if (isVelocityFraud) fraudCount += 2;
            if (isPatternFraud) fraudCount += 2;
            if (isUnusualFrequency) fraudCount += 1;
            if (isSimilarToRecent) fraudCount += 1;

            if (fraudCount >= 5 || isDuplicate || isHistoricalDuplicate) {
                return AlertLevel.CRITICAL;
            } else if (fraudCount >= 3) {
                return AlertLevel.HIGH;
            } else if (fraudCount >= 2) {
                return AlertLevel.MEDIUM;
            } else {
                return AlertLevel.LOW;
            }
        }

        private void logFraudChecks(String accountId, String chequeNumber, double amount,
                                    boolean isDuplicate, boolean isAbnormal, boolean isSuspicious,
                                    boolean isVelocityFraud, boolean isPatternFraud,
                                    boolean isHistoricalDuplicate, boolean isUnusualFrequency,
                                    boolean isSimilarToRecent) {
            System.out.println("\n===== FRAUD CHECK REPORT =====");
            System.out.println("Account: " + accountId + ", Cheque: " + chequeNumber + ", Amount: " + amount);

            System.out.println("\n--- Basic Checks ---");
            System.out.println("Duplicate Check: " + formatCheckResult(isDuplicate));
            System.out.println("Abnormal Amount Check: " + formatCheckResult(isAbnormal));
            System.out.println("Suspicious Activity Check: " + formatCheckResult(isSuspicious));
            System.out.println("Velocity Check: " + formatCheckResult(isVelocityFraud));
            System.out.println("Pattern Analysis: " + formatCheckResult(isPatternFraud));

            if (historyManager != null) {
                System.out.println("\n--- Advanced Checks ---");
                System.out.println("Historical Duplicate Check: " + formatCheckResult(isHistoricalDuplicate));
                System.out.println("Unusual Frequency Check: " + formatCheckResult(isUnusualFrequency));
                System.out.println("Similar Recent Amount Check: " + formatCheckResult(isSimilarToRecent));
            }

            boolean anyFraudDetected = isDuplicate || isAbnormal || isSuspicious ||
                    isVelocityFraud || isPatternFraud ||
                    isHistoricalDuplicate || isUnusualFrequency || isSimilarToRecent;

            System.out.println("\n--- Summary ---");
            if (anyFraudDetected) {
                System.out.println("⚠️ FRAUD ALERT: Potential fraud detected!");
            } else {
                System.out.println("✓ No fraud detected.");
            }
            System.out.println("=============================\n");
        }

        private String formatCheckResult(boolean failed) {
            return failed ? "FAILED ⚠️" : "Passed ✓";
        }

        private static class ChequeTransaction {
            private double amount;
            private java.time.LocalDate date;

            public ChequeTransaction(double amount, java.time.LocalDate date) {
                this.amount = amount;
                this.date = date;
            }

            public double getAmount() {
                return amount;
            }

            public java.time.LocalDate getDate() {
                return date;
            }
        }
    }

    /**
     * Service for detecting fraudulent cheque activities version2.
     * Implements various fraud detection mechanisms and uses ChequeHistoryManager version2.
     */
    static class FraudDetectionServiceV1 {
        private FraudDetection fraudDetection;
        private ChequeHistoryManager historyManager;
        private Map<String, List<ChequeTransaction>> recentTransactions;

        // Fraud detection thresholds
        private static final int VELOCITY_CHECK_DAYS = 7;
        private static final int VELOCITY_THRESHOLD = 5;
        private static final double PATTERN_THRESHOLD = 0.95; // 95% similarity threshold
        private static final double SIMILAR_AMOUNT_THRESHOLD = 0.90; // 90% similarity threshold
        private static final int UNUSUAL_FREQUENCY_THRESHOLD = 3; // 3x normal frequency

        // Fraud alert levels
        public enum AlertLevel {
            LOW,
            MEDIUM,
            HIGH,
            CRITICAL
        }

        public FraudDetectionServiceV1() {
            this.fraudDetection = new FraudDetection();
            this.recentTransactions = new HashMap<>();
        }

        public void setHistoryManager(ChequeHistoryManager historyManager) {
            this.historyManager = historyManager;
        }

        public boolean isFraudulentCheque(String accountId, String chequeNumber, double amount) {
            boolean isDuplicate = checkDuplicateCheque(accountId, chequeNumber);
            boolean isAbnormal = checkAbnormalAmount(amount);
            boolean isSuspicious = checkSuspiciousActivity(accountId, amount);
            boolean isVelocityFraud = checkVelocityFraud(accountId, amount);
            boolean isPatternFraud = checkPatternFraud(accountId, amount);

            boolean isHistoricalDuplicate = false;
            boolean isUnusualFrequency = false;
            boolean isSimilarToRecent = false;

            if (historyManager != null) {
                isHistoricalDuplicate = checkHistoricalDuplicate(accountId, chequeNumber);
                isUnusualFrequency = checkUnusualFrequency(accountId);
                isSimilarToRecent = checkSimilarToRecent(accountId, amount);
            }

            logFraudChecks(accountId, chequeNumber, amount, isDuplicate, isAbnormal,
                    isSuspicious, isVelocityFraud, isPatternFraud,
                    isHistoricalDuplicate, isUnusualFrequency, isSimilarToRecent);

            AlertLevel alertLevel = determineAlertLevel(isDuplicate, isAbnormal,
                    isSuspicious, isVelocityFraud, isPatternFraud,
                    isHistoricalDuplicate, isUnusualFrequency, isSimilarToRecent);

            System.out.println("Fraud Alert Level: " + alertLevel);

            return isDuplicate || isAbnormal || isSuspicious || isVelocityFraud || isPatternFraud ||
                    isHistoricalDuplicate || isUnusualFrequency || isSimilarToRecent;
        }

        private boolean checkDuplicateCheque(String accountId, String chequeNumber) {
            return fraudDetection.isDuplicateCheque(accountId, chequeNumber);
        }

        private boolean checkAbnormalAmount(double amount) {
            return fraudDetection.isAbnormalAmount(amount);
        }

        private boolean checkSuspiciousActivity(String accountId, double amount) {
            return fraudDetection.isSuspiciousActivity(accountId, amount);
        }

        private boolean checkVelocityFraud(String accountId, double amount) {
            if (!recentTransactions.containsKey(accountId)) {
                recentTransactions.put(accountId, new ArrayList<>());
            }
            ChequeTransaction currentTransaction = new ChequeTransaction(amount, java.time.LocalDate.now());
            List<ChequeTransaction> transactions = recentTransactions.get(accountId);
            transactions.add(currentTransaction);

            java.time.LocalDate cutoffDate = java.time.LocalDate.now().minusDays(VELOCITY_CHECK_DAYS);
            long recentCount = transactions.stream()
                    .filter(t -> !t.getDate().isBefore(cutoffDate))
                    .count();

            // Clean up old transactions
            recentTransactions.put(accountId, transactions.stream()
                    .filter(t -> !t.getDate().isBefore(cutoffDate))
                    .toList());

            return recentCount > VELOCITY_THRESHOLD;
        }

        private boolean checkPatternFraud(String accountId, double amount) {
            if (!recentTransactions.containsKey(accountId)) {
                return false;
            }
            List<ChequeTransaction> transactions = recentTransactions.get(accountId);
            if (transactions.size() < 3) {
                return false;
            }
            List<Double> amounts = transactions.stream()
                    .map(ChequeTransaction::getAmount)
                    .toList();
            double similarCount = 0;
            for (Double pastAmount : amounts) {
                double similarity = 1.0 - Math.abs(pastAmount - amount) / Math.max(pastAmount, amount);
                if (similarity > PATTERN_THRESHOLD) {
                    similarCount++;
                }
            }
            return similarCount >= 3;
        }

        private boolean checkHistoricalDuplicate(String accountId, String chequeNumber) {
            List<String> historicalCheques = historyManager.getChequeNumbers(accountId);
            return historicalCheques.contains(chequeNumber);
        }

        private boolean checkUnusualFrequency(String accountId) {
            int totalCheques = historyManager.getTotalChequeCount(accountId);
            int recentCheques = historyManager.getRecentChequeCount(accountId);
            if (totalCheques < 10) {
                return false;
            }
            double avgMonthlyFrequency = totalCheques / 3.0;
            return recentCheques > avgMonthlyFrequency * UNUSUAL_FREQUENCY_THRESHOLD;
        }

        private boolean checkSimilarToRecent(String accountId, double amount) {
            return historyManager.hasSimilarRecentCheque(accountId, amount, SIMILAR_AMOUNT_THRESHOLD);
        }

        private AlertLevel determineAlertLevel(boolean isDuplicate, boolean isAbnormal,
                                               boolean isSuspicious, boolean isVelocityFraud,
                                               boolean isPatternFraud, boolean isHistoricalDuplicate,
                                               boolean isUnusualFrequency, boolean isSimilarToRecent) {
            int fraudCount = 0;
            if (isDuplicate || isHistoricalDuplicate) fraudCount += 3;
            if (isAbnormal) fraudCount += 2;
            if (isSuspicious) fraudCount += 2;
            if (isVelocityFraud) fraudCount += 2;
            if (isPatternFraud) fraudCount += 2;
            if (isUnusualFrequency) fraudCount += 1;
            if (isSimilarToRecent) fraudCount += 1;

            if (fraudCount >= 5 || isDuplicate || isHistoricalDuplicate) {
                return AlertLevel.CRITICAL;
            } else if (fraudCount >= 3) {
                return AlertLevel.HIGH;
            } else if (fraudCount >= 2) {
                return AlertLevel.MEDIUM;
            } else {
                return AlertLevel.LOW;
            }
        }

        private void logFraudChecks(String accountId, String chequeNumber, double amount,
                                    boolean isDuplicate, boolean isAbnormal, boolean isSuspicious,
                                    boolean isVelocityFraud, boolean isPatternFraud,
                                    boolean isHistoricalDuplicate, boolean isUnusualFrequency,
                                    boolean isSimilarToRecent) {
            System.out.println("\n===== FRAUD CHECK REPORT =====");
            System.out.println("Account: " + accountId + ", Cheque: " + chequeNumber + ", Amount: " + amount);

            System.out.println("\n--- Basic Checks ---");
            System.out.println("Duplicate Check: " + formatCheckResult(isDuplicate));
            System.out.println("Abnormal Amount Check: " + formatCheckResult(isAbnormal));
            System.out.println("Suspicious Activity Check: " + formatCheckResult(isSuspicious));
            System.out.println("Velocity Check: " + formatCheckResult(isVelocityFraud));
            System.out.println("Pattern Analysis: " + formatCheckResult(isPatternFraud));

            if (historyManager != null) {
                System.out.println("\n--- Advanced Checks ---");
                System.out.println("Historical Duplicate Check: " + formatCheckResult(isHistoricalDuplicate));
                System.out.println("Unusual Frequency Check: " + formatCheckResult(isUnusualFrequency));
                System.out.println("Similar Recent Amount Check: " + formatCheckResult(isSimilarToRecent));
            }

            boolean anyFraudDetected = isDuplicate || isAbnormal || isSuspicious ||
                    isVelocityFraud || isPatternFraud ||
                    isHistoricalDuplicate || isUnusualFrequency || isSimilarToRecent;

            System.out.println("\n--- Summary ---");
            if (anyFraudDetected) {
                System.out.println("⚠️ FRAUD ALERT: Potential fraud detected!");
            } else {
                System.out.println("✓ No fraud detected.");
            }
            System.out.println("=============================\n");
        }

        private String formatCheckResult(boolean failed) {
            return failed ? "FAILED ⚠️" : "Passed ✓";
        }

        private static class ChequeTransaction {
            private double amount;
            private java.time.LocalDate date;

            public ChequeTransaction(double amount, java.time.LocalDate date) {
                this.amount = amount;
                this.date = date;
            }

            public double getAmount() {
                return amount;
            }

            public java.time.LocalDate getDate() {
                return date;
            }
        }
    }

        /**
     * Service for detecting fraudulent cheque activities version3.
     * Implements various fraud detection mechanisms and uses ChequeHistoryManager version3.
     */
    static class FraudDetectionServiceV2 {
        private FraudDetection fraudDetection;
        private ChequeHistoryManager historyManager;
        private Map<String, List<ChequeTransaction>> recentTransactions;
        private Map<String, Integer> duplicateChequeCounter;
        private Map<String, List<Double>> abnormalAmounts;
        private Map<String, List<Double>> suspiciousAmounts;
        private Map<String, List<Double>> velocityAmounts;
        private Map<String, List<Double>> patternAmounts;
        private Map<String, List<Double>> historicalDuplicateAmounts;
        private Map<String, List<Double>> unusualFrequencyAmounts;
        private Map<String, List<Double>> similarToRecentAmounts;
        private List<String> fraudLogs;
        private int totalFraudChecks;

        // Fraud detection thresholds
        private static final int VELOCITY_CHECK_DAYS = 7;
        private static final int VELOCITY_THRESHOLD = 5;
        private static final double PATTERN_THRESHOLD = 0.95; // 95% similarity threshold
        private static final double SIMILAR_AMOUNT_THRESHOLD = 0.90; // 90% similarity threshold
        private static final int UNUSUAL_FREQUENCY_THRESHOLD = 3; // 3x normal frequency

        // Fraud alert levels
        public enum AlertLevel {
            LOW,
            MEDIUM,
            HIGH,
            CRITICAL
        }

        public FraudDetectionServiceV2() {
            this.fraudDetection = new FraudDetection();
            this.recentTransactions = new HashMap<>();
            this.duplicateChequeCounter = new HashMap<>();
            this.abnormalAmounts = new HashMap<>();
            this.suspiciousAmounts = new HashMap<>();
            this.velocityAmounts = new HashMap<>();
            this.patternAmounts = new HashMap<>();
            this.historicalDuplicateAmounts = new HashMap<>();
            this.unusualFrequencyAmounts = new HashMap<>();
            this.similarToRecentAmounts = new HashMap<>();
            this.fraudLogs = new ArrayList<>();
            this.totalFraudChecks = 0;
        }

        public FraudDetectionServiceV2(ChequeHistoryManager historyManager) {
            this.fraudDetection = new FraudDetection();
            this.recentTransactions = new HashMap<>();
            this.duplicateChequeCounter = new HashMap<>();
            this.abnormalAmounts = new HashMap<>();
            this.suspiciousAmounts = new HashMap<>();
            this.velocityAmounts = new HashMap<>();
            this.patternAmounts = new HashMap<>();
            this.historicalDuplicateAmounts = new HashMap<>();
            this.unusualFrequencyAmounts = new HashMap<>();
            this.similarToRecentAmounts = new HashMap<>();
            this.fraudLogs = new ArrayList<>();
            this.totalFraudChecks = 0;
            this.historyManager = historyManager;
        }

        public boolean isFraudulentCheque(String accountId, String chequeNumber, double amount) {
            totalFraudChecks++;
            boolean isDuplicate = checkDuplicateCheque(accountId, chequeNumber);
            boolean isAbnormal = checkAbnormalAmount(amount);
            boolean isSuspicious = checkSuspiciousActivity(accountId, amount);
            boolean isVelocityFraud = checkVelocityFraud(accountId, amount);
            boolean isPatternFraud = checkPatternFraud(accountId, amount);

            boolean isHistoricalDuplicate = false;
            boolean isUnusualFrequency = false;
            boolean isSimilarToRecent = false;

            if (historyManager != null) {
                isHistoricalDuplicate = checkHistoricalDuplicate(accountId, chequeNumber);
                isUnusualFrequency = checkUnusualFrequency(accountId);
                isSimilarToRecent = checkSimilarToRecent(accountId, amount);
            }

            logFraudChecks(accountId, chequeNumber, amount, isDuplicate, isAbnormal,
                    isSuspicious, isVelocityFraud, isPatternFraud,
                    isHistoricalDuplicate, isUnusualFrequency, isSimilarToRecent);

            AlertLevel alertLevel = determineAlertLevel(isDuplicate, isAbnormal,
                    isSuspicious, isVelocityFraud, isPatternFraud,
                    isHistoricalDuplicate, isUnusualFrequency, isSimilarToRecent);

            System.out.println("Fraud Alert Level: " + alertLevel);

            return isDuplicate || isAbnormal || isSuspicious || isVelocityFraud || isPatternFraud ||
                    isHistoricalDuplicate || isUnusualFrequency || isSimilarToRecent;
        }

        private boolean checkDuplicateCheque(String accountId, String chequeNumber) {
            return fraudDetection.isDuplicateCheque(accountId, chequeNumber);
        }

        private boolean checkAbnormalAmount(double amount) {
            return fraudDetection.isAbnormalAmount(amount);
        }

        private boolean checkSuspiciousActivity(String accountId, double amount) {
            return fraudDetection.isSuspiciousActivity(accountId, amount);
        }

        private boolean checkVelocityFraud(String accountId, double amount) {
            if (!recentTransactions.containsKey(accountId)) {
                recentTransactions.put(accountId, new ArrayList<>());
            }
            ChequeTransaction currentTransaction = new ChequeTransaction(amount, java.time.LocalDate.now());
            List<ChequeTransaction> transactions = recentTransactions.get(accountId);
            transactions.add(currentTransaction);

            java.time.LocalDate cutoffDate = java.time.LocalDate.now().minusDays(VELOCITY_CHECK_DAYS);
            long recentCount = transactions.stream()
                    .filter(t -> !t.getDate().isBefore(cutoffDate))
                    .count();

            // Clean up old transactions
            recentTransactions.put(accountId, transactions.stream()
                    .filter(t -> !t.getDate().isBefore(cutoffDate))
                    .toList());

            return recentCount > VELOCITY_THRESHOLD;
        }

        private boolean checkPatternFraud(String accountId, double amount) {
            if (!recentTransactions.containsKey(accountId)) {
                return false;
            }
            List<ChequeTransaction> transactions = recentTransactions.get(accountId);
            if (transactions.size() < 3) {
                return false;
            }
            List<Double> amounts = transactions.stream()
                    .map(ChequeTransaction::getAmount)
                    .toList();
            double similarCount = 0;
            for (Double pastAmount : amounts) {
                double similarity = 1.0 - Math.abs(pastAmount - amount) / Math.max(pastAmount, amount);
                if (similarity > PATTERN_THRESHOLD) {
                    similarCount++;
                }
            }
            return similarCount >= 3;
        }

        private boolean checkHistoricalDuplicate(String accountId, String chequeNumber) {
            List<String> historicalCheques = historyManager.getChequeNumbers(accountId);
            return historicalCheques.contains(chequeNumber);
        }

        private boolean checkUnusualFrequency(String accountId) {
            int totalCheques = historyManager.getTotalChequeCount(accountId);
            int recentCheques = historyManager.getRecentChequeCount(accountId);
            if (totalCheques < 10) {
                return false;
            }
            double avgMonthlyFrequency = totalCheques / 3.0;
            return recentCheques > avgMonthlyFrequency * UNUSUAL_FREQUENCY_THRESHOLD;
        }

        private boolean checkSimilarToRecent(String accountId, double amount) {
            return historyManager.hasSimilarRecentCheque(accountId, amount, SIMILAR_AMOUNT_THRESHOLD);
        }

        private AlertLevel determineAlertLevel(boolean isDuplicate, boolean isAbnormal,
                                               boolean isSuspicious, boolean isVelocityFraud,
                                               boolean isPatternFraud, boolean isHistoricalDuplicate,
                                               boolean isUnusualFrequency, boolean isSimilarToRecent) {
            int fraudCount = 0;
            if (isDuplicate || isHistoricalDuplicate) fraudCount += 3;
            if (isAbnormal) fraudCount += 2;
            if (isSuspicious) fraudCount += 2;
            if (isVelocityFraud) fraudCount += 2;
            if (isPatternFraud) fraudCount += 2;
            if (isUnusualFrequency) fraudCount += 1;
            if (isSimilarToRecent) fraudCount += 1;

            if (fraudCount >= 5 || isDuplicate || isHistoricalDuplicate) {
                return AlertLevel.CRITICAL;
            } else if (fraudCount >= 3) {
                return AlertLevel.HIGH;
            } else if (fraudCount >= 2) {
                return AlertLevel.MEDIUM;
            } else {
                return AlertLevel.LOW;
            }
        }

        private void logFraudChecks(String accountId, String chequeNumber, double amount,
                                    boolean isDuplicate, boolean isAbnormal, boolean isSuspicious,
                                    boolean isVelocityFraud, boolean isPatternFraud,
                                    boolean isHistoricalDuplicate, boolean isUnusualFrequency,
                                    boolean isSimilarToRecent) {
            System.out.println("\n===== FRAUD CHECK REPORT =====");
            System.out.println("Account: " + accountId + ", Cheque: " + chequeNumber + ", Amount: " + amount);

            System.out.println("\n--- Basic Checks ---");
            System.out.println("Duplicate Check: " + formatCheckResult(isDuplicate));
            System.out.println("Abnormal Amount Check: " + formatCheckResult(isAbnormal));
            System.out.println("Suspicious Activity Check: " + formatCheckResult(isSuspicious));
            System.out.println("Velocity Check: " + formatCheckResult(isVelocityFraud));
            System.out.println("Pattern Analysis: " + formatCheckResult(isPatternFraud));

            if (historyManager != null) {
                System.out.println("\n--- Advanced Checks ---");
                System.out.println("Historical Duplicate Check: " + formatCheckResult(isHistoricalDuplicate));
                System.out.println("Unusual Frequency Check: " + formatCheckResult(isUnusualFrequency));
                System.out.println("Similar Recent Amount Check: " + formatCheckResult(isSimilarToRecent));
            }

            boolean anyFraudDetected = isDuplicate || isAbnormal || isSuspicious ||
                    isVelocityFraud || isPatternFraud ||
                    isHistoricalDuplicate || isUnusualFrequency || isSimilarToRecent;

            System.out.println("\n--- Summary ---");
            if (anyFraudDetected) {
                System.out.println("⚠️ FRAUD ALERT: Potential fraud detected!");
            } else {
                System.out.println("✓ No fraud detected.");
            }
        }

        private String formatCheckResult(boolean failed) {
            return failed ? "FAILED ⚠️" : "Passed ✓";
        }

        private static class ChequeTransaction {
            private double amount;
            private java.time.LocalDate date;

            public ChequeTransaction(double amount, java.time.LocalDate date) {
                this.amount = amount;
                this.date = date;
            }

            public double getAmount() {
                return amount;
            }

            public java.time.LocalDate getDate() {
                return date;
            }
        }
    }

    /**
     * Core fraud detection class that implements fundamental fraud detection mechanisms.
     */
    static class FraudDetection {
        private static final double ABNORMAL_AMOUNT_THRESHOLD = 10000.0;
        private static final double SUSPICIOUS_ACTIVITY_MULTIPLIER = 10.0;
        private static final double AMOUNT_VARIANCE_THRESHOLD = 0.05;

        private Map<String, Set<String>> chequeRegistry = new HashMap<>();
        private Map<String, Double> accountActivity = new HashMap<>();
        private Map<String, List<TransactionRecord>> accountTransactionHistory = new HashMap<>();
        private Map<String, AccountProfile> accountProfiles = new HashMap<>();

        public boolean isDuplicateCheque(String accountId, String chequeNumber) {
            if (!chequeRegistry.containsKey(accountId)) {
                chequeRegistry.put(accountId, new HashSet<>());
            }
            Set<String> processedCheques = chequeRegistry.get(accountId);
            if (processedCheques.contains(chequeNumber)) {
                return true;
            }
            processedCheques.add(chequeNumber);
            return false;
        }

        public boolean isAbnormalAmount(double amount) {
            return amount > ABNORMAL_AMOUNT_THRESHOLD;
        }

        public boolean isSuspiciousActivity(String accountId, double amount) {
            double totalActivity = accountActivity.containsKey(accountId) ?
                    accountActivity.get(accountId) : 0.0;
            totalActivity += amount;
            accountActivity.put(accountId, totalActivity);
            recordTransaction(accountId, amount);
            updateAccountProfile(accountId, amount);
            boolean exceedsThreshold = totalActivity > ABNORMAL_AMOUNT_THRESHOLD * SUSPICIOUS_ACTIVITY_MULTIPLIER;
            boolean abnormalBehavior = isAbnormalBehavior(accountId, amount);
            return exceedsThreshold || abnormalBehavior;
        }

        private void recordTransaction(String accountId, double amount) {
            if (!accountTransactionHistory.containsKey(accountId)) {
                accountTransactionHistory.put(accountId, new ArrayList<>());
            }
            List<TransactionRecord> history = accountTransactionHistory.get(accountId);
            history.add(new TransactionRecord(amount, java.time.LocalDateTime.now()));
            java.time.LocalDateTime cutoff = java.time.LocalDateTime.now().minusDays(90);
            accountTransactionHistory.put(accountId, history.stream()
                    .filter(record -> record.timestamp.isAfter(cutoff))
                    .toList());
        }

        private void updateAccountProfile(String accountId, double amount) {
            if (!accountProfiles.containsKey(accountId)) {
                accountProfiles.put(accountId, new AccountProfile());
            }
            AccountProfile profile = accountProfiles.get(accountId);
            profile.updateWithTransaction(amount);
        }

        private boolean isAbnormalBehavior(String accountId, double amount) {
            if (!accountProfiles.containsKey(accountId)) {
                return false;
            }
            AccountProfile profile = accountProfiles.get(accountId);
            if (profile.transactionCount >= 5) {
                double avgAmount = profile.totalAmount / profile.transactionCount;
                double variance = Math.abs(amount - avgAmount) / avgAmount;
                return variance > AMOUNT_VARIANCE_THRESHOLD && amount > avgAmount;
            }
            return false;
        }

        private static class TransactionRecord {
            private double amount;
            private java.time.LocalDateTime timestamp;

            public TransactionRecord(double amount, java.time.LocalDateTime timestamp) {
                this.amount = amount;
                this.timestamp = timestamp;
            }
        }

        private static class AccountProfile {
            private double totalAmount = 0.0;
            private int transactionCount = 0;
            private double maxAmount = 0.0;
            private double minAmount = Double.MAX_VALUE;

            public void updateWithTransaction(double amount) {
                totalAmount += amount;
                transactionCount++;
                maxAmount = Math.max(maxAmount, amount);
                minAmount = Math.min(minAmount, amount);
            }
        }
    }

    /**
     * AdminService for master data and batch/transaction management.
     */
    static class AdminService {
        // Master data: IFSC and bank codes
        private Map<String, String> ifscToBankCode = new HashMap<>();
        private Map<String, String> bankCodeToName = new HashMap<>();

        // Batch management
        private Map<String, List<BatchCheque>> batches = new HashMap<>();
        // Stuck transactions (for demo, just a list of cheque numbers)
        private Set<String> stuckTransactions = new HashSet<>();

        // --- Master Data Management ---
        public void addOrUpdateIFSC(String ifsc, String bankCode) {
            ifscToBankCode.put(ifsc, bankCode);
            System.out.println("IFSC " + ifsc + " mapped to bank code " + bankCode);
        }

        public void addOrUpdateBankCode(String bankCode, String bankName) {
            bankCodeToName.put(bankCode, bankName);
            System.out.println("Bank code " + bankCode + " mapped to bank name " + bankName);
        }

        public void displayIFSCs() {
            System.out.println("\n--- IFSC to Bank Code Mapping ---");
            if (ifscToBankCode.isEmpty()) {
                System.out.println("No IFSC records.");
            } else {
                ifscToBankCode.forEach((ifsc, code) -> System.out.println("IFSC: " + ifsc + " -> Bank Code: " + code));
            }
        }

        public void displayBankCodes() {
            System.out.println("\n--- Bank Code to Name Mapping ---");
            if (bankCodeToName.isEmpty()) {
                System.out.println("No bank code records.");
            } else {
                bankCodeToName.forEach((code, name) -> System.out.println("Bank Code: " + code + " -> Name: " + name));
            }
        }

        // --- Batch Management ---
        public void createBatch(String batchId, List<BatchCheque> cheques) {
            batches.put(batchId, new ArrayList<>(cheques));
            System.out.println("Batch " + batchId + " created with " + cheques.size() + " cheques.");
        }

        public void displayBatches() {
            System.out.println("\n--- Batch List ---");
            if (batches.isEmpty()) {
                System.out.println("No batches available.");
            } else {
                batches.forEach((batchId, cheques) -> {
                    System.out.println("Batch ID: " + batchId + " | Cheques: " + cheques.size());
                });
            }
        }

        public void displayBatchDetails(String batchId) {
            List<BatchCheque> cheques = batches.get(batchId);
            if (cheques == null) {
                System.out.println("Batch not found.");
                return;
            }
            System.out.println("Batch " + batchId + " details:");
            for (BatchCheque cheque : cheques) {
                System.out.printf("Account: %s | Cheque: %s | Amount: %.2f | Currency: %s\n",
                    cheque.accountNumber, cheque.chequeNumber, cheque.amount, cheque.currency);
            }
        }

        // --- Stuck Transaction Management ---
        public void markTransactionStuck(String chequeNumber) {
            stuckTransactions.add(chequeNumber);
            System.out.println("Cheque " + chequeNumber + " marked as stuck.");
        }

        public void resetStuckTransaction(String chequeNumber) {
            if (stuckTransactions.remove(chequeNumber)) {
                System.out.println("Cheque " + chequeNumber + " reset (removed from stuck list).");
            } else {
                System.out.println("Cheque " + chequeNumber + " was not marked as stuck.");
            }
        }

        public void displayStuckTransactions() {
            System.out.println("\n--- Stuck Transactions ---");
            if (stuckTransactions.isEmpty()) {
                System.out.println("No stuck transactions.");
            } else {
                stuckTransactions.forEach(cheque -> System.out.println("Cheque: " + cheque));
            }
        }
    }
}



/**
 * Represents a user of the system (employee or account holder).
 */
static class User {
    private String username;
    private String password; // In a real app, this would be hashed
    private String role; // e.g., "EMPLOYEE", "ACCOUNT_HOLDER"

    public User(String username, String password, String role) {
        this.username = username;
        this.password = password;
        this.role = role;
    }

    public String getUsername() {
        return username;
    }

    public String getPassword() {
        return password;
    }

    public String getRole() {
        return role;
    }
}

    /**
     * Service for managing users and handling authentication.
     */
static class UserService {
    private Map<String, User> users = new HashMap<>();

    public UserService() {
        // Add some sample users for demonstration
        registerUser("employee1", "password123", "EMPLOYEE");
        registerUser("account1001", "chequeuser", "ACCOUNT_HOLDER");
        registerUser("account1002", "securepass", "ACCOUNT_HOLDER");
    }

    /**
     * Registers a new user.
     * @param username The username
     * @param password The password
     * @param role The user's role
     */
    public void registerUser(String username, String password, String role) {
        users.put(username, new User(username, password, role));
        System.out.println("User registered: " + username + " (" + role + ")");
    }

    /**
     * Authenticates a user based on username and password.
     * @param username The username
     * @param password The password
     * @return The authenticated User object if successful, null otherwise
     */
    public User authenticate(String username, String password) {
        User user = users.get(username);
        if (user != null && user.getPassword().equals(password)) {
            System.out.println("Authentication successful for user: " + username);
            return user;
        }
        System.out.println("Authentication failed for user: " + username);
        return null;
    }
}

    /**
     * Represents a single cheque transaction for batch processing.
     */
class BatchCheque {
    String accountNumber;
    String chequeNumber;
    String currency;
    double amount;
    String signature;

    public BatchCheque(String accountNumber, String chequeNumber, String currency, double amount, String signature) {
        this.accountNumber = accountNumber;
        this.chequeNumber = chequeNumber;
        this.currency = currency;
        this.amount = amount;
        this.signature = signature;
    }
}

    /**
     * Create application class for the Cheque Processing System.
     * This system processes cheques with fraud detection capabilities.
     */
public class CreateApplication {
    public static void main(String[] args) {
        User authenticatedUser = null;
        Scanner scanner = new Scanner(System.in);

        System.out.println("Starting Cheque Processing System with Enhanced Fraud Detection...");
        
        // Initialize services
        CurrencyExchangeService currencyExchangeService = new CurrencyExchangeService();
        SignatureVerificationService signatureVerificationService = new SignatureVerificationService();
        CoreBankingSystemUpdater coreBankingSystemUpdater = new CoreBankingSystemUpdater();
        UserService userService = new UserService(); // Initialize UserService
        ChequeHistoryManager chequeHistoryManager = new ChequeHistoryManager();
        FraudDetectionService fraudDetectionService = new FraudDetectionService();

        // Set up dependencies
        fraudDetectionService.setHistoryManager(chequeHistoryManager);

        System.out.println("System initialized successfully.");

        // --- Login Process ---
        authenticatedUser = performLogin(scanner, userService);
        if (authenticatedUser == null) {
            System.out.println("Maximum login attempts reached. Exiting.");
            return; // Exit if login fails after retries
        }

        // Initialize cheque processor
        ChequeProcessor chequeProcessor = new ChequeProcessor(currencyExchangeService, signatureVerificationService,
                coreBankingSystemUpdater, chequeHistoryManager, fraudDetectionService);
        
        System.out.println("System initialized successfully.");
  
        while (authenticatedUser != null) { // Continue loop only if authenticated
            System.out.println("\n--- Cheque Processing System ---");  
            System.out.println("1. Process a Single Cheque");  
            System.out.println("2. Process Multiple Cheques (Batch)");
            System.out.println("3. View Cheque History");  
            System.out.println("4. Currency Exchange Information");  
            System.out.println("5. Generate Cheque Reports");
            System.out.println("6. Exit");  
            System.out.print("Enter your choice: ");  
            int choice = scanner.nextInt();  
            scanner.nextLine(); // Consume newline  
  
            switch (choice) {  
                case 1:  
                    System.out.println("Enter account number:");  
                    String accountNumber = scanner.nextLine();  
  
                    System.out.println("Enter cheque number:");  
                    String chequeNumber = scanner.nextLine();  
  
                    System.out.println("Enter currency (e.g., USD, EUR, GBP):");  
                    String currency = scanner.nextLine();  
  
                    System.out.println("Enter amount:");  
                    double amount = scanner.nextDouble();  
                    scanner.nextLine(); // Consume newline  
  
                    System.out.println("Enter signature:");  
                    String signature = scanner.nextLine();  
  
                    // Process the cheque  
                    chequeProcessor.processCheque(accountNumber, chequeNumber, currency, amount, signature);  
                    break;  
  
                case 2:
                    // Process multiple cheques in a batch
                    processChequeBatch(scanner, chequeProcessor);
                    break;

                case 3:  
                    System.out.println("Enter account number to view cheque history:");  
                    String historyAccountNumber = scanner.nextLine();  
                    chequeHistoryManager.displayChequeHistory(historyAccountNumber);  
                    break;  
  
                case 4:
                    displayCurrencyExchangeMenu(scanner, currencyExchangeService);
                    break;
                    
                case 5:
                    handleReportGeneration(scanner, chequeHistoryManager);
                    break;

                case 6:  
                    System.out.println("Exiting...");  
                    scanner.close();  
                    return;  
  
                default:  
                    System.out.println("Invalid choice. Please try again.");  
            }
        }
    }

    /**
     * Handles the user login process.
     * @param scanner The scanner for user input
     * @param userService The user service for authentication
     * @return The authenticated User object, or null if login fails after retries
     */
    private static User performLogin(Scanner scanner, UserService userService) {
        final int MAX_ATTEMPTS = 3;
        for (int attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
            System.out.println("\n--- Login ---");
            System.out.print("Enter username: ");
            String username = scanner.nextLine();
            System.out.print("Enter password: ");
            String password = scanner.nextLine(); // In a real app, use a secure way to read password

            User user = userService.authenticate(username, password);
            if (user != null) {
                System.out.println("Welcome, " + user.getUsername() + " (" + user.getRole() + ")!");
                return user; // Login successful
            } else {
                System.out.println("Invalid username or password. Attempt " + attempt + " of " + MAX_ATTEMPTS);
            }
        }
        return null; // Login failed after max attempts
    }

    /**
     * Handles processing multiple cheques in a batch.
     * Prompts the user for the number of cheques and their details.
     * @param scanner The scanner for user input
     * @param chequeProcessor The cheque processor service
     */
    private static void processChequeBatch(Scanner scanner, ChequeProcessor chequeProcessor) {
        System.out.println("\n--- Batch Cheque Processing ---");
        System.out.print("Enter the number of cheques in the batch: ");
        int batchSize = scanner.nextInt();
        scanner.nextLine(); // Consume newline

        List<BatchCheque> chequesToProcess = new ArrayList<>();

        for (int i = 0; i < batchSize; i++) {
            System.out.println("\nEnter details for Cheque #" + (i + 1) + ":");
            System.out.print("Account number: ");
            String accountNumber = scanner.nextLine();
            System.out.print("Cheque number: ");
            String chequeNumber = scanner.nextLine();
            System.out.print("Currency (e.g., USD, EUR, GBP): ");
            String currency = scanner.nextLine();
            System.out.print("Amount: ");
            double amount = scanner.nextDouble();
            scanner.nextLine(); // Consume newline
            System.out.print("Signature: ");
            String signature = scanner.nextLine();

            chequesToProcess.add(new BatchCheque(accountNumber, chequeNumber, currency, amount, signature));
        }

        System.out.println("\nProcessing batch...");
        chequesToProcess.forEach(cheque -> chequeProcessor.processCheque(cheque.accountNumber, cheque.chequeNumber, cheque.currency, cheque.amount, cheque.signature));
    }
    
    /**
     * Display the currency exchange menu and handle user interactions
     * @param scanner The scanner for user input
     * @param currencyExchangeService The currency exchange service
     */
    private static void displayCurrencyExchangeMenu(Scanner scanner, CurrencyExchangeService currencyExchangeService) {
        while (true) {
            System.out.println("\n--- Currency Exchange Menu ---");
            System.out.println("1. View Supported Currencies");
            System.out.println("2. Get Exchange Rate");
            System.out.println("3. Get Detailed Exchange Rate Information");
            System.out.println("4. Convert Currency");
            System.out.println("5. Return to Main Menu");
            System.out.print("Enter your choice: ");
            
            int choice = scanner.nextInt();
            scanner.nextLine(); // Consume newline
            
            switch (choice) {
                case 1:
                    // Display supported currencies
                    List<String> supportedCurrencies = currencyExchangeService.getSupportedCurrencies();
                    System.out.println("\nSupported Currencies:");
                    for (String currencyCode : supportedCurrencies) {
                        System.out.println("- " + currencyCode);
                    }
                    break;
                    
                case 2:
                    // Get exchange rate
                    System.out.print("Enter currency code: ");
                    String currencyCode = scanner.nextLine().toUpperCase();
                    double rate = currencyExchangeService.getExchangeRate(currencyCode);
                    
                    if (rate > 0) {
                        System.out.println("Exchange rate for " + currencyCode + ": " + rate);
                    } else {
                        System.out.println("Currency not supported or exchange rate unavailable.");
                    }
                    break;
                    
                case 3:
                    // Get detailed exchange rate information
                    System.out.print("Enter currency code: ");
                    String detailCurrencyCode = scanner.nextLine().toUpperCase();
                    Map<String, Double> detailedRates = currencyExchangeService.getDetailedExchangeRates(detailCurrencyCode);
                    
                    if (!detailedRates.isEmpty()) {
                        System.out.println("\nDetailed Exchange Rate Information for " + detailCurrencyCode + ":");
                        System.out.println("Mid Rate: " + detailedRates.get("mid"));
                        System.out.println("Buy Rate: " + detailedRates.get("buy"));
                        System.out.println("Sell Rate: " + detailedRates.get("sell"));
                        System.out.println("Fee Rate: " + detailedRates.get("fee"));
                    } else {
                        System.out.println("Currency not supported or exchange rate unavailable.");
                    }
                    break;
                    
                case 4:
                    // Convert currency
                    System.out.print("Enter amount: ");
                    double amount = scanner.nextDouble();
                    scanner.nextLine(); // Consume newline
                    
                    System.out.print("Enter source currency code: ");
                    String fromCurrency = scanner.nextLine().toUpperCase();
                    
                    System.out.print("Enter target currency code: ");
                    String toCurrency = scanner.nextLine().toUpperCase();
                    
                    double convertedAmount = currencyExchangeService.convertCurrency(amount, fromCurrency, toCurrency);
                    
                    if (convertedAmount > 0) {
                        System.out.printf("%.2f %s = %.2f %s\n", amount, fromCurrency, convertedAmount, toCurrency);
                    } else {
                        System.out.println("Currency conversion failed. Please check the currency codes.");
                    }
                    break;
                    
                case 5:
                    // Return to main menu
                    return;
                    
                default:
                    System.out.println("Invalid choice. Please try again.");
            }
        }
    }

    /**
     * Handles the report generation menu and logic.
     * @param scanner The scanner for user input
     * @param chequeHistoryManager The cheque history manager
     */
    private static void handleReportGeneration(Scanner scanner, ChequeHistoryManager chequeHistoryManager) {
        System.out.println("\n--- Generate Cheque Reports ---");
        System.out.println("1. Daily Report (Today)");
        System.out.println("2. Weekly Report (Last 7 Days)");
        System.out.println("3. Monthly Report (Last 30 Days)");
        System.out.println("4. Custom Date Range Report");
        System.out.println("5. Return to Main Menu");
        System.out.print("Enter your choice: ");
        int choice = scanner.nextInt();
        scanner.nextLine(); // Consume newline

        LocalDate endDate = LocalDate.now();
        LocalDate startDate;
        String reportNamePrefix;

        switch (choice) {
            case 1: // Daily
                startDate = endDate;
                reportNamePrefix = "daily_report_";
                break;
            case 2: // Weekly
                startDate = endDate.minusDays(6); // Last 7 days including today
                reportNamePrefix = "weekly_report_";
                break;
            case 3: // Monthly
                startDate = endDate.minusDays(29); // Last 30 days including today
                reportNamePrefix = "monthly_report_";
                break;
            case 4: // Custom
                System.out.print("Enter start date (YYYY-MM-DD): ");
                String startDateStr = scanner.nextLine();
                System.out.print("Enter end date (YYYY-MM-DD): ");
                String endDateStr = scanner.nextLine();
                try {
                    startDate = LocalDate.parse(startDateStr, DateTimeFormatter.ISO_LOCAL_DATE);
                    endDate = LocalDate.parse(endDateStr, DateTimeFormatter.ISO_LOCAL_DATE);
                } catch (Exception e) {
                    System.out.println("Invalid date format. Please use YYYY-MM-DD.");
                    return;
                }
                if (startDate.isAfter(endDate)) {
                    System.out.println("Start date cannot be after end date.");
                    return;
                }
                reportNamePrefix = "custom_report_";
                break;
            case 5:
                return; // Return to main menu
            default:
                System.out.println("Invalid choice. Please try again.");
                return;
        }

        List<ChequeHistoryManager.ChequeRecord> records = chequeHistoryManager.getAllChequeRecordsInPeriod(startDate, endDate);

        if (records.isEmpty()) {
            System.out.println("No cheque records found for the selected period.");
            return;
        }

        String csvData = chequeHistoryManager.generateChequeReportCSV(records);
        String fileName = reportNamePrefix + startDate.format(DateTimeFormatter.ISO_LOCAL_DATE) +
                          "_to_" + endDate.format(DateTimeFormatter.ISO_LOCAL_DATE) + ".csv";

        try (BufferedWriter writer = new BufferedWriter(new FileWriter(fileName))) {
            writer.write(csvData);
            System.out.println("Report generated successfully: " + fileName);
        } catch (IOException e) {
            System.err.println("Error writing report to file: " + e.getMessage());
        }
    }


    // --- Existing Inner Classes (User, UserService, BatchCheque) ---
    // ... (Keep existing inner classes as they are)

    /**
     * Service for verifying signatures on cheques.
     * This is a simplified implementation for demonstration purposes.
     */
    static class SignatureVerificationService {
        private Map<String, String> accountSignatures = new HashMap<>();

        public SignatureVerificationService() {
            // Initialize with some sample signatures for testing
            accountSignatures.put("1001", "John Doe");
            accountSignatures.put("1002", "Jane Smith");
            accountSignatures.put("1003", "Robert Johnson");
        }

        /**
         * Verifies if the provided signature matches the one on file for the account.
         *
         * @param accountNumber The account number
         * @param signature The signature to verify
         * @return true if the signature is valid, false otherwise
         */
        public boolean verifySignature(String accountNumber, String signature) {
            System.out.println("Verifying signature for account: " + accountNumber);

            // If we don't have a signature on file, accept any signature (for demo purposes)
            if (!accountSignatures.containsKey(accountNumber)) {
                System.out.println("No signature on file for account: " + accountNumber + ". Accepting new signature.");
                accountSignatures.put(accountNumber, signature);
                return true;
            }

            // Compare the provided signature with the one on file
            String storedSignature = accountSignatures.get(accountNumber);
            boolean isValid = storedSignature.equals(signature);

            if (isValid) {
                System.out.println("Signature verified successfully.");
            } else {
                System.out.println("Signature verification failed.");
            }

            return isValid;
        }

        /**
         * Updates the signature on file for an account.
         *
         * @param accountNumber The account number
         * @param newSignature The new signature
         */
        public void updateSignature(String accountNumber, String newSignature) {
            accountSignatures.put(accountNumber, newSignature);
            System.out.println("Signature updated for account: " + accountNumber);
        }
    }

    /**
     * Module for processing cheques with signature verification, fraud detection,
     * currency conversion, and core banking system update.
     */
    static class ChequeProcessor {
        private CurrencyExchangeService currencyExchangeService;
        private SignatureVerificationService signatureVerificationService;
        private CoreBankingSystemUpdater coreBankingSystemUpdater;
        private ChequeHistoryManager chequeHistoryManager;
        private FraudDetectionService fraudDetectionService;

        public ChequeProcessor(CurrencyExchangeService currencyExchangeService,
                               SignatureVerificationService signatureVerificationService,
                               CoreBankingSystemUpdater coreBankingSystemUpdater,
                               ChequeHistoryManager chequeHistoryManager,
                               FraudDetectionService fraudDetectionService) {
            this.currencyExchangeService = currencyExchangeService;
            this.signatureVerificationService = signatureVerificationService;
            this.coreBankingSystemUpdater = coreBankingSystemUpdater;
            this.chequeHistoryManager = chequeHistoryManager;
            this.fraudDetectionService = fraudDetectionService;
        }

        public void processCheque(String accountNumber, String chequeNumber, String currency, double amount, String signature) {
            System.out.println("Processing cheque...");

            // Step 1: Verify signature
            if (!signatureVerificationService.verifySignature(accountNumber, signature)) {
                System.out.println("Signature verification failed. Cheque processing aborted.");
                return;
            }

            // Step 2: Fraud detection
            if (fraudDetectionService.isFraudulentCheque(accountNumber, chequeNumber, amount)) {
                System.out.println("Fraudulent cheque detected. Cheque processing aborted.");
                return;
            }

            // Step 3: Get detailed exchange rate information if currency is not local
            double amountInLocalCurrency = amount;
            if (!"USD".equalsIgnoreCase(currency)) { // USD is the base currency
                Map<String, Double> detailedRates = currencyExchangeService.getDetailedExchangeRates(currency);

                if (detailedRates.isEmpty()) {
                    System.out.println("Failed to fetch exchange rate. Cheque processing aborted.");
                    return;
                }

                // Use the buy rate for incoming transactions
                double buyRate = detailedRates.get("buy");
                double fee = detailedRates.get("fee");

                // Step 4: Convert amount to local currency with detailed calculations
                amountInLocalCurrency = amount * buyRate;
                double feeAmount = amount * fee;

                System.out.println("Currency: " + currency.toUpperCase());
                System.out.println("Original amount: " + amount);
                System.out.println("Exchange rate (buy): " + buyRate);
                System.out.println("Fee rate: " + fee);
                System.out.println("Fee amount: " + feeAmount);
                System.out.println("Amount in local currency (before fees): " + amountInLocalCurrency);

                // Apply fee
                amountInLocalCurrency -= feeAmount;
                System.out.println("Final amount in local currency (USD): " + amountInLocalCurrency);
            } else {
                System.out.println("Processing in local currency (USD): " + amountInLocalCurrency);
            }

            // Step 5: Update core banking system
            coreBankingSystemUpdater.updateCoreBankingSystem(accountNumber, amountInLocalCurrency);

            // Step 6: Record cheque history
            chequeHistoryManager.recordCheque(accountNumber, chequeNumber, currency, amount, new java.util.Date());

            System.out.println("Cheque processed successfully.");
        }
    }

    /**
     * Enhanced Currency Exchange Service
     * Supports multiple currencies with detailed exchange rate calculations
     * and dynamic fetching of rates from external sources.
     */
    static class CurrencyExchangeService {
        private Map<String, CurrencyRate> exchangeRateCache = new HashMap<>();
        private static final String BASE_CURRENCY = "USD";
        private static final long CACHE_EXPIRY_MINUTES = 60; // Cache expiry time in minutes
        private static final String API_KEY = "demo"; // Replace with your actual API key for production

        // Fallback exchange rates in case API is unavailable
        private static final Map<String, Double> FALLBACK_RATES = new HashMap<String, Double>() {{
            put("EUR", 1.1);
            put("GBP", 1.3);
            put("INR", 0.013);
            put("JPY", 0.0091);
            put("CAD", 0.74);
            put("AUD", 0.67);
            put("CHF", 1.12);
            put("CNY", 0.14);
            put("HKD", 0.13);
            put("NZD", 0.62);
        }};

        /**
         * Get the exchange rate for a specific currency
         * @param currency The currency code (e.g., EUR, GBP)
         * @return The exchange rate relative to the base currency (USD)
         */
        public double getExchangeRate(String currency) {
            System.out.println("Fetching exchange rate for currency: " + currency);

            // Standardize currency code
            String currencyCode = currency.toUpperCase();

            // Return 1.0 if it's the base currency
            if (BASE_CURRENCY.equals(currencyCode)) {
                return 1.0;
            }

            // Check cache first
            if (isCacheValid(currencyCode)) {
                CurrencyRate cachedRate = exchangeRateCache.get(currencyCode);
                System.out.println("Using cached rate: " + cachedRate.getRate() + " (Last updated: " +
                        cachedRate.getLastUpdated().format(java.time.format.DateTimeFormatter.ISO_LOCAL_DATE_TIME) + ")");
                return cachedRate.getRate();
            }

            // Try to fetch from external API
            try {
                double apiRate = fetchRateFromAPI(currencyCode);
                if (apiRate > 0) {
                    // Cache the new rate
                    exchangeRateCache.put(currencyCode, new CurrencyRate(apiRate, java.time.LocalDateTime.now()));
                    return apiRate;
                }
            } catch (Exception e) {
                System.out.println("Error fetching exchange rate from API: " + e.getMessage());
                // Continue to fallback rates
            }

            // Use fallback rates if API fetch failed
            Double fallbackRate = FALLBACK_RATES.get(currencyCode);
            if (fallbackRate != null) {
                System.out.println("Using fallback rate for " + currencyCode + ": " + fallbackRate);
                // Cache the fallback rate
                exchangeRateCache.put(currencyCode, new CurrencyRate(fallbackRate, java.time.LocalDateTime.now()));
                return fallbackRate;
            }

            System.out.println("No exchange rate available for currency: " + currencyCode);
            return 0.0;
        }

        /**
         * Convert an amount from one currency to another
         * @param amount The amount to convert
         * @param fromCurrency The source currency
         * @param toCurrency The target currency
         * @return The converted amount
         */
        public double convertCurrency(double amount, String fromCurrency, String toCurrency) {
            double fromRate = getExchangeRate(fromCurrency);
            double toRate = getExchangeRate(toCurrency);

            if (fromRate <= 0 || toRate <= 0) {
                System.out.println("Cannot convert: invalid exchange rates");
                return 0.0;
            }

            // Convert to base currency first, then to target currency
            double amountInBaseCurrency = amount * fromRate;
            double convertedAmount = amountInBaseCurrency / toRate;

            System.out.println(String.format("Converted %.2f %s to %.2f %s",
                    amount, fromCurrency.toUpperCase(), convertedAmount, toCurrency.toUpperCase()));

            return convertedAmount;
        }

        /**
         * Get detailed exchange rate information including buy/sell rates and fees
         * @param currency The currency code
         * @return A map containing detailed rate information
         */
        public Map<String, Double> getDetailedExchangeRates(String currency) {
            String currencyCode = currency.toUpperCase();
            double baseRate = getExchangeRate(currencyCode);

            if (baseRate <= 0) {
                return Collections.emptyMap();
            }

            Map<String, Double> detailedRates = new HashMap<>();
            detailedRates.put("mid", baseRate);

            // Calculate buy rate (slightly lower than mid rate)
            double buyRate = baseRate * 0.99;
            detailedRates.put("buy", buyRate);

            // Calculate sell rate (slightly higher than mid rate)
            double sellRate = baseRate * 1.01;
            detailedRates.put("sell", sellRate);

            // Calculate fees
            double fee = baseRate * 0.005; // 0.5% fee
            detailedRates.put("fee", fee);

            return detailedRates;
        }

        /**
         * Get a list of all supported currencies
         * @return A list of supported currency codes
         */
        public List<String> getSupportedCurrencies() {
            List<String> currencies = new ArrayList<>();
            currencies.add(BASE_CURRENCY);
            currencies.addAll(FALLBACK_RATES.keySet());

            // Sort alphabetically
            Collections.sort(currencies);
            return currencies;
        }

        /**
         * Check if the cached rate is still valid
         * @param currency The currency code
         * @return true if the cache is valid, false otherwise
         */
        private boolean isCacheValid(String currency) {
            if (!exchangeRateCache.containsKey(currency)) {
                return false;
            }

            CurrencyRate cachedRate = exchangeRateCache.get(currency);
            java.time.LocalDateTime now = java.time.LocalDateTime.now();
            java.time.LocalDateTime expiryTime = cachedRate.getLastUpdated().plusMinutes(CACHE_EXPIRY_MINUTES);

            return now.isBefore(expiryTime);
        }

        /**
         * Fetch exchange rate from an external API
         * @param currency The currency code
         * @return The exchange rate
         * @throws Exception If there's an error fetching the rate
         */
        private double fetchRateFromAPI(String currency) throws Exception {
            // Using Open Exchange Rates API as an example
            // In a real application, you would use a proper API key
            String apiUrl = "https://open.er-api.com/v6/latest/" + BASE_CURRENCY + "?apikey=" + API_KEY;

            try {
                java.net.URL url = new java.net.URL(apiUrl);
                java.net.HttpURLConnection connection = (java.net.HttpURLConnection) url.openConnection();
                connection.setRequestMethod("GET");
                connection.setConnectTimeout(5000);
                connection.setReadTimeout(5000);

                int status = connection.getResponseCode();
                if (status != 200) {
                    throw new Exception("API returned status code: " + status);
                }

                java.io.BufferedReader reader = new java.io.BufferedReader(new java.io.InputStreamReader(connection.getInputStream()));
                StringBuilder response = new StringBuilder();
                String line;
                while ((line = reader.readLine()) != null) {
                    response.append(line);
                }
                reader.close();

                // Parse JSON response
                org.json.simple.parser.JSONParser parser = new org.json.simple.parser.JSONParser();
                org.json.simple.JSONObject jsonObject = (org.json.simple.JSONObject) parser.parse(response.toString());
                org.json.simple.JSONObject rates = (org.json.simple.JSONObject) jsonObject.get("rates");

                if (rates != null && rates.containsKey(currency)) {
                    double rate = ((Number) rates.get(currency)).doubleValue();
                    System.out.println("Fetched rate from API for " + currency + ": " + rate);
                    return rate;
                } else {
                    throw new Exception("Currency not found in API response");
                }
            } catch (Exception e) {
                System.out.println("API fetch failed: " + e.getMessage());
                throw e;
            }
        }

        /**
         * Clear the exchange rate cache
         */
        public void clearCache() {
            exchangeRateCache.clear();
            System.out.println("Exchange rate cache cleared");
        }
    }

    /**
     * Class to store currency rate information with timestamp
     */
    static class CurrencyRate {
        private double rate;
        private java.time.LocalDateTime lastUpdated;

        public CurrencyRate(double rate, java.time.LocalDateTime lastUpdated) {
            this.rate = rate;
            this.lastUpdated = lastUpdated;
        }

        public double getRate() {
            return rate;
        }

        public java.time.LocalDateTime getLastUpdated() {
            return lastUpdated;
        }
    }

    /**
     * Service for detecting fraudulent cheque activities.
     * Implements various fraud detection mechanisms and uses ChequeHistoryManager.
     */
    static class FraudDetectionService {
        private FraudDetection fraudDetection;
        private ChequeHistoryManager historyManager;
        private Map<String, List<ChequeTransaction>> recentTransactions;

        // Fraud detection thresholds
        private static final int VELOCITY_CHECK_DAYS = 7;
        private static final int VELOCITY_THRESHOLD = 5;
        private static final double PATTERN_THRESHOLD = 0.95; // 95% similarity threshold
        private static final double SIMILAR_AMOUNT_THRESHOLD = 0.90; // 90% similarity threshold
        private static final int UNUSUAL_FREQUENCY_THRESHOLD = 3; // 3x normal frequency

        // Fraud alert levels
        public enum AlertLevel {
            LOW,
            MEDIUM,
            HIGH,
            CRITICAL
        }

        public FraudDetectionService() {
            this.fraudDetection = new FraudDetection();
            this.recentTransactions = new HashMap<>();
        }

        public void setHistoryManager(ChequeHistoryManager historyManager) {
            this.historyManager = historyManager;
        }

        public boolean isFraudulentCheque(String accountId, String chequeNumber, double amount) {
            boolean isDuplicate = checkDuplicateCheque(accountId, chequeNumber);
            boolean isAbnormal = checkAbnormalAmount(amount);
            boolean isSuspicious = checkSuspiciousActivity(accountId, amount);
            boolean isVelocityFraud = checkVelocityFraud(accountId, amount);
            boolean isPatternFraud = checkPatternFraud(accountId, amount);

            boolean isHistoricalDuplicate = false;
            boolean isUnusualFrequency = false;
            boolean isSimilarToRecent = false;

            if (historyManager != null) {
                isHistoricalDuplicate = checkHistoricalDuplicate(accountId, chequeNumber);
                isUnusualFrequency = checkUnusualFrequency(accountId);
                isSimilarToRecent = checkSimilarToRecent(accountId, amount);
            }

            logFraudChecks(accountId, chequeNumber, amount, isDuplicate, isAbnormal,
                    isSuspicious, isVelocityFraud, isPatternFraud,
                    isHistoricalDuplicate, isUnusualFrequency, isSimilarToRecent);

            AlertLevel alertLevel = determineAlertLevel(isDuplicate, isAbnormal,
                    isSuspicious, isVelocityFraud, isPatternFraud,
                    isHistoricalDuplicate, isUnusualFrequency, isSimilarToRecent);

            System.out.println("Fraud Alert Level: " + alertLevel);

            return isDuplicate || isAbnormal || isSuspicious || isVelocityFraud || isPatternFraud ||
                    isHistoricalDuplicate || isUnusualFrequency || isSimilarToRecent;
        }

        private boolean checkDuplicateCheque(String accountId, String chequeNumber) {
            return fraudDetection.isDuplicateCheque(accountId, chequeNumber);
        }

        private boolean checkAbnormalAmount(double amount) {
            return fraudDetection.isAbnormalAmount(amount);
        }

        private boolean checkSuspiciousActivity(String accountId, double amount) {
            return fraudDetection.isSuspiciousActivity(accountId, amount);
        }

        private boolean checkVelocityFraud(String accountId, double amount) {
            if (!recentTransactions.containsKey(accountId)) {
                recentTransactions.put(accountId, new ArrayList<>());
            }
            ChequeTransaction currentTransaction = new ChequeTransaction(amount, java.time.LocalDate.now());
            List<ChequeTransaction> transactions = recentTransactions.get(accountId);
            transactions.add(currentTransaction);

            java.time.LocalDate cutoffDate = java.time.LocalDate.now().minusDays(VELOCITY_CHECK_DAYS);
            long recentCount = transactions.stream()
                    .filter(t -> !t.getDate().isBefore(cutoffDate))
                    .count();

            // Clean up old transactions
            recentTransactions.put(accountId, transactions.stream()
                    .filter(t -> !t.getDate().isBefore(cutoffDate))
                    .toList());

            return recentCount > VELOCITY_THRESHOLD;
        }

        private boolean checkPatternFraud(String accountId, double amount) {
            if (!recentTransactions.containsKey(accountId)) {
                return false;
            }
            List<ChequeTransaction> transactions = recentTransactions.get(accountId);
            if (transactions.size() < 3) {
                return false;
            }
            List<Double> amounts = transactions.stream()
                    .map(ChequeTransaction::getAmount)
                    .toList();
            double similarCount = 0;
            for (Double pastAmount : amounts) {
                double similarity = 1.0 - Math.abs(pastAmount - amount) / Math.max(pastAmount, amount);
                if (similarity > PATTERN_THRESHOLD) {
                    similarCount++;
                }
            }
            return similarCount >= 3;
        }

        private boolean checkHistoricalDuplicate(String accountId, String chequeNumber) {
            List<String> historicalCheques = historyManager.getChequeNumbers(accountId);
            return historicalCheques.contains(chequeNumber);
        }

        private boolean checkUnusualFrequency(String accountId) {
            int totalCheques = historyManager.getTotalChequeCount(accountId);
            int recentCheques = historyManager.getRecentChequeCount(accountId);
            if (totalCheques < 10) {
                return false;
            }
            double avgMonthlyFrequency = totalCheques / 3.0;
            return recentCheques > avgMonthlyFrequency * UNUSUAL_FREQUENCY_THRESHOLD;
        }

        private boolean checkSimilarToRecent(String accountId, double amount) {
            return historyManager.hasSimilarRecentCheque(accountId, amount, SIMILAR_AMOUNT_THRESHOLD);
        }

        private AlertLevel determineAlertLevel(boolean isDuplicate, boolean isAbnormal,
                                               boolean isSuspicious, boolean isVelocityFraud,
                                               boolean isPatternFraud, boolean isHistoricalDuplicate,
                                               boolean isUnusualFrequency, boolean isSimilarToRecent) {
            int fraudCount = 0;
            if (isDuplicate || isHistoricalDuplicate) fraudCount += 3;
            if (isAbnormal) fraudCount += 2;
            if (isSuspicious) fraudCount += 2;
            if (isVelocityFraud) fraudCount += 2;
            if (isPatternFraud) fraudCount += 2;
            if (isUnusualFrequency) fraudCount += 1;
            if (isSimilarToRecent) fraudCount += 1;

            if (fraudCount >= 5 || isDuplicate || isHistoricalDuplicate) {
                return AlertLevel.CRITICAL;
            } else if (fraudCount >= 3) {
                return AlertLevel.HIGH;
            } else if (fraudCount >= 2) {
                return AlertLevel.MEDIUM;
            } else {
                return AlertLevel.LOW;
            }
        }

        private void logFraudChecks(String accountId, String chequeNumber, double amount,
                                    boolean isDuplicate, boolean isAbnormal, boolean isSuspicious,
                                    boolean isVelocityFraud, boolean isPatternFraud,
                                    boolean isHistoricalDuplicate, boolean isUnusualFrequency,
                                    boolean isSimilarToRecent) {
            System.out.println("\n===== FRAUD CHECK REPORT =====");
            System.out.println("Account: " + accountId + ", Cheque: " + chequeNumber + ", Amount: " + amount);

            System.out.println("\n--- Basic Checks ---");
            System.out.println("Duplicate Check: " + formatCheckResult(isDuplicate));
            System.out.println("Abnormal Amount Check: " + formatCheckResult(isAbnormal));
            System.out.println("Suspicious Activity Check: " + formatCheckResult(isSuspicious));
            System.out.println("Velocity Check: " + formatCheckResult(isVelocityFraud));
            System.out.println("Pattern Analysis: " + formatCheckResult(isPatternFraud));

            if (historyManager != null) {
                System.out.println("\n--- Advanced Checks ---");
                System.out.println("Historical Duplicate Check: " + formatCheckResult(isHistoricalDuplicate));
                System.out.println("Unusual Frequency Check: " + formatCheckResult(isUnusualFrequency));
                System.out.println("Similar Recent Amount Check: " + formatCheckResult(isSimilarToRecent));
            }

            boolean anyFraudDetected = isDuplicate || isAbnormal || isSuspicious ||
                    isVelocityFraud || isPatternFraud ||
                    isHistoricalDuplicate || isUnusualFrequency || isSimilarToRecent;

            System.out.println("\n--- Summary ---");
            if (anyFraudDetected) {
                System.out.println("⚠️ FRAUD ALERT: Potential fraud detected!");
            } else {
                System.out.println("✓ No fraud detected.");
            }
            System.out.println("=============================\n");
        }

        private String formatCheckResult(boolean failed) {
            return failed ? "FAILED ⚠️" : "Passed ✓";
        }

        private static class ChequeTransaction {
            private double amount;
            private java.time.LocalDate date;

            public ChequeTransaction(double amount, java.time.LocalDate date) {
                this.amount = amount;
                this.date = date;
            }

            public double getAmount() {
                return amount;
            }

            public java.time.LocalDate getDate() {
                return date;
            }
        }
    }

    /**
     * Core fraud detection class that implements fundamental fraud detection mechanisms.
     */
    static class FraudDetection {
        private static final double ABNORMAL_AMOUNT_THRESHOLD = 10000.0;
        private static final double SUSPICIOUS_ACTIVITY_MULTIPLIER = 10.0;
        private static final double AMOUNT_VARIANCE_THRESHOLD = 0.05;

        private Map<String, Set<String>> chequeRegistry = new HashMap<>();
        private Map<String, Double> accountActivity = new HashMap<>();
        private Map<String, List<TransactionRecord>> accountTransactionHistory = new HashMap<>();
        private Map<String, AccountProfile> accountProfiles = new HashMap<>();

        public boolean isDuplicateCheque(String accountId, String chequeNumber) {
            if (!chequeRegistry.containsKey(accountId)) {
                chequeRegistry.put(accountId, new HashSet<>());
            }
            Set<String> processedCheques = chequeRegistry.get(accountId);
            if (processedCheques.contains(chequeNumber)) {
                return true;
            }
            processedCheques.add(chequeNumber);
            return false;
        }

        public boolean isAbnormalAmount(double amount) {
            return amount > ABNORMAL_AMOUNT_THRESHOLD;
        }

        public boolean isSuspiciousActivity(String accountId, double amount) {
            double totalActivity = accountActivity.containsKey(accountId) ?
                    accountActivity.get(accountId) : 0.0;
            totalActivity += amount;
            accountActivity.put(accountId, totalActivity);
            recordTransaction(accountId, amount);
            updateAccountProfile(accountId, amount);
            boolean exceedsThreshold = totalActivity > ABNORMAL_AMOUNT_THRESHOLD * SUSPICIOUS_ACTIVITY_MULTIPLIER;
            boolean abnormalBehavior = isAbnormalBehavior(accountId, amount);
            return exceedsThreshold || abnormalBehavior;
        }

        private void recordTransaction(String accountId, double amount) {
            if (!accountTransactionHistory.containsKey(accountId)) {
                accountTransactionHistory.put(accountId, new ArrayList<>());
            }
            List<TransactionRecord> history = accountTransactionHistory.get(accountId);
            history.add(new TransactionRecord(amount, java.time.LocalDateTime.now()));
            java.time.LocalDateTime cutoff = java.time.LocalDateTime.now().minusDays(90);
            accountTransactionHistory.put(accountId, history.stream()
                    .filter(record -> record.timestamp.isAfter(cutoff))
                    .toList());
        }

        private void updateAccountProfile(String accountId, double amount) {
            if (!accountProfiles.containsKey(accountId)) {
                accountProfiles.put(accountId, new AccountProfile());
            }
            AccountProfile profile = accountProfiles.get(accountId);
            profile.updateWithTransaction(amount);
        }

        private boolean isAbnormalBehavior(String accountId, double amount) {
            if (!accountProfiles.containsKey(accountId)) {
                return false;
            }
            AccountProfile profile = accountProfiles.get(accountId);
            if (profile.transactionCount >= 5) {
                double avgAmount = profile.totalAmount / profile.transactionCount;
                double variance = Math.abs(amount - avgAmount) / avgAmount;
                return variance > AMOUNT_VARIANCE_THRESHOLD && amount > avgAmount;
            }
            return false;
        }

        private static class TransactionRecord {
            private double amount;
            private java.time.LocalDateTime timestamp;

            public TransactionRecord(double amount, java.time.LocalDateTime timestamp) {
                this.amount = amount;
                this.timestamp = timestamp;
            }
        }

        private static class AccountProfile {
            private double totalAmount = 0.0;
            private int transactionCount = 0;
            private double maxAmount = 0.0;
            private double minAmount = Double.MAX_VALUE;

            public void updateWithTransaction(double amount) {
                totalAmount += amount;
                transactionCount++;
                maxAmount = Math.max(maxAmount, amount);
                minAmount = Math.min(minAmount, amount);
            }
        }
    }
}

import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';
import csv from 'csv-parser';
import moment from 'moment';

// Get IP address and admin username from environment variables
const course = process.env.COURSE;
const user = process.env.USER;
const password = process.env.PASSWORD;
const ipAddress = process.env.IP_ADDRESS;
const csvFilePath = process.env.CSV_FILE_PATH;
const outputFile = process.env.OUTPUT_FILE;

if (!user || !password) {
  const message = "User and Password not provided. Please provide the Admin User and Password of the host through the environment variable."
  console.log(`Error: ${message}`);
  writeToFile("Error", message)
  process.exit(1); // Exit if the file path is not provided
}

if (!course || !ipAddress) {
  const message = "Course or Host Ip not provided. Please provide the Course and Host Ip through the environment variable."
  console.log(`Error: ${message}`);
  writeToFile("Error", message)
  process.exit(1); // Exit if the file path is not provided
}

if (!csvFilePath || !outputFile) {
  const message = "CSV and Output file path not provided. Please provide the CSV and Output file path through the environment variable."
  console.log(`Error: ${message}`);
  writeToFile("Error", message)
  process.exit(1); // Exit if the file path is not provided
}

const users = [];
const successCount = { count: 0 };
const failureCount = { count: 0 };

// Define the path to save unenrolled users with timestamp

// Function to write to the CSV file
function writeToFile(user, message) {
  const timestamp = moment().format('DD:MM:YYYY,hh:mm A'); // Format the timestamp using moment
  const logEntry = `${user}, ${timestamp}, ${ipAddress}, ${message}\n`
  fs.appendFileSync(outputFile, logEntry, 'utf8');
}

// Function to load users from CSV
async function loadUsersFromCSV(filePath) {
  return new Promise((resolve, reject) => {
    fs.createReadStream(path.resolve(filePath))
      .pipe(csv())
      .on('data', (row) => {
        console.log("Row read from CSV:", row); // Log the entire row for debugging
        // Trim the keys to avoid issues with whitespace
        const trimmedRow = Object.fromEntries(
          Object.entries(row).map(([key, value]) => [key.trim(), value])
        );

        // Ensure the username is correctly accessed from the trimmed row
        if (trimmedRow.username) {
          users.push(trimmedRow.username);
        } else {
          console.error("Username not found in row:", trimmedRow);
        }
      })
      .on('end', () => {
        resolve();
      })
      .on('error', (error) => {
        reject(error);
      });
  });
}
test('test', async ({ page }) => {
  await loadUsersFromCSV(csvFilePath); // Load users from the CSV file

  // Construct the URL dynamically with the IP address
  const loginURL = `http://${ipAddress}:8000/hub/login?next=%2Fhub%2F`;

  await page.goto(loginURL);
  await page.getByLabel('Username:').fill(user);
  await page.getByLabel('Password:').fill(password);
  await page.getByRole('button', { name: 'Sign In' }).click();
  console.log('signed in successfully')
  const isLoginError = await page.locator('text=Invalid username or password.').isVisible();
  if (isLoginError) {
    console.log("Login failed: Invalid username or password.");
    process.exit(1);
  }
  
  await page.getByText('File', { exact: true }).click();
  const page1Promise = page.waitForEvent('popup');
  await page.locator('#jp-mainmenu-file').getByText('Hub Control Panel').click();
  const page1 = await page1Promise;
  await expect(page1.getByRole('link', { name: 'Admin' })).toBeVisible();
  await page1.getByRole('link', { name: 'Admin' }).click();
  console.log('Clicked on the admin hub users list')

  await page1.getByRole('button', { name: 'Manage Groups' }).click();
  await page1.getByRole('link', { name: `nbgrader-${course}` }).click();
  console.log('selected the course to unenroll the students list')

  for (const user of users) {
    console.log(`no of users ${users.length}`)
    console.log("user", user)
    try {
      // Check if the user is visible before attempting to click
      const userElement = page1.locator(`text=${user}`);
      if (await userElement.isVisible()) {

        await userElement.click();
        successCount.count++;
        writeToFile(user, "Successfully Un-Enrolled");
      } else {
        failureCount.count++;
        writeToFile(user, "User Not Found or not visible");
      }
    } catch (error) {
      failureCount.count++;
      writeToFile(user, "Error clicking user");
    }
  }
  await page1.getByTestId('submit').click();
  await page1.getByRole('button', { name: 'Logout' }).click();
  writeToFile("Over_View", `Total users clicked successfully: ${successCount.count}, Total users failed to click: ${failureCount.count}`);
});

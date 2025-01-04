import unittest
import sys
import logging

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test_run.log')
    ]
)

logger = logging.getLogger(__name__)

if __name__ == '__main__':
    logger.info("Starting test run...")
    
    # Load tests
    try:
        test_suite = unittest.TestLoader().discover('.', pattern='tests.py')
        logger.info("Test suite loaded successfully")
    except Exception as e:
        logger.error("Failed to load test suite: %s", str(e))
        sys.exit(1)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Log results
    logger.info("Tests completed:")
    logger.info("  Ran %d tests", result.testsRun)
    logger.info("  Failures: %d", len(result.failures))
    logger.info("  Errors: %d", len(result.errors))
    
    # Log failures and errors
    if result.failures:
        logger.error("Failures:")
        for failure in result.failures:
            logger.error("  %s", failure[0])
            logger.error("  %s", failure[1])
    
    if result.errors:
        logger.error("Errors:")
        for error in result.errors:
            logger.error("  %s", error[0])
            logger.error("  %s", error[1])
    
    # Exit with appropriate status code
    sys.exit(len(result.failures) + len(result.errors))
